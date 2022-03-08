import abc
import datetime
import itertools
import operator
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Type

from playhouse.shortcuts import model_to_dict

from robotoff import settings
from robotoff.brands import BRAND_PREFIX_STORE, in_barcode_range
from robotoff.insights.dataclass import InsightType
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import Prediction as PredictionModel
from robotoff.models import ProductInsight, batch_insert
from robotoff.off import get_server_type
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.products import (
    DBProductStore,
    Product,
    get_image_id,
    get_product_store,
    is_valid_image,
)
from robotoff.taxonomy import Taxonomy, get_taxonomy
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.cache import CachedStore

logger = get_logger(__name__)


def load_authorized_labels() -> Set[str]:
    return set(text_file_iter(settings.OCR_LABEL_WHITELIST_DATA_PATH))


AUTHORIZED_LABELS_STORE = CachedStore(load_authorized_labels, expiration_interval=None)


def is_selected_image(images: Dict[str, Any], image_id: str) -> bool:
    """Return True if the image referenced by `image_id` is selected as a
    front, ingredients, nutrition or packaging image in any language.

    :param images: The image dict as stored in MongoDB.
    :param image_id: The image ID to compare, must be a digit.
    """
    for key_prefix in ("front", "ingredients", "nutrition", "packaging"):
        for key, image in images.items():
            if key.startswith(key_prefix) and image["imgid"] == image_id:
                return True

    return False


def is_recent_image(
    images: Dict[str, Any], image_id: str, max_timedelta: datetime.timedelta
) -> bool:
    """Return True if the image referenced by `image_id` is less than
    `max_timedelta` older than the most recent image, return False otherwise.

    Only "raw" images (images identified with digits) are compared to the
    provided `image_id`.

    :param images: The image dict as stored in MongoDB.
    :param image_id: The image ID to compare, must be a digit.
    :param max_timedelta: The maximum interval between the upload datetime of
    the most recent image and the provided image.
    """
    image_datetime = datetime.datetime.utcfromtimestamp(
        int(images[image_id]["uploaded_t"])
    )
    remaining_datetimes = []
    for key, image_meta in images.items():
        if key.isdigit() and key != image_id:
            remaining_datetimes.append(
                datetime.datetime.utcfromtimestamp(int(image_meta["uploaded_t"]))
            )

    for upload_datetime in remaining_datetimes:
        if upload_datetime - image_datetime > max_timedelta:
            logger.info(
                "More recent image: {} > {}".format(upload_datetime, image_datetime)
            )
            return False

    return True


def is_valid_insight_image(images: Dict[str, Any], source_image: Optional[str]):
    """Return True if the source image is valid for insight generation,
    i.e. the image ID is a digit and is referenced in `images`.

    If `source_image` is None, we always consider the insight as valid.

    :param images: The image dict as stored in MongoDB.
    :param source_image: The insight source image, should be the path of the
    image path or None.
    """
    if source_image is None:
        return True

    image_id = Path(source_image).stem
    return image_id.isdigit() and image_id in images


def is_trustworthy_insight_image(
    images: Dict[str, Any],
    source_image: Optional[str],
    max_timedelta: datetime.timedelta = settings.IMAGE_MAX_TIMEDELTA,
):
    """Return True if the source image is trustworthy for insight generation,
      - the image ID is a digit and is referenced in `images`
      - the image is either selected or recent enough

    If `source_image` is None, we always consider the insight as trustworthy.
    Insights considered as trustworthy can have automatic_processing = True.

    :param images: The image dict as stored in MongoDB.
    :param source_image: The insight source image, should be the path of the
    image path or None.
    :param max_timedelta: Maximum timedelta between most recent image and
    source image, default settings.IMAGE_MAX_TIMEDELTA.
    """
    if source_image is None:
        return True

    image_id = Path(source_image).stem

    if not image_id.isdigit() or image_id not in images:
        return False

    return is_selected_image(images, image_id) or is_recent_image(
        images, image_id, max_timedelta
    )


def get_existing_insight(
    insight_type: InsightType, barcode: str, server_domain: str
) -> List[ProductInsight]:
    """Get `value` and `value_tag` of all insights for specific product and
    `insight_type`."""
    return list(
        ProductInsight.select(
            ProductInsight.annotation,
            ProductInsight.id,
            ProductInsight.value,
            ProductInsight.value_tag,
        ).where(
            ProductInsight.type == insight_type.name,
            ProductInsight.barcode == barcode,
            ProductInsight.server_domain == server_domain,
        )
    )


def is_reserved_barcode(barcode: str) -> bool:
    if barcode.startswith("0"):
        barcode = barcode[1:]

    return barcode.startswith("2")


def sort_predictions(predictions: Iterable[Prediction]) -> List[Prediction]:
    """Sort predictions by priority, using as keys:
    - priority, specified by data["priority"], prediction with lowest priority
    values (high priority) come first
    - source image upload datetime (most recent first): images IDs are
    auto-incremented integers, so the most recent images have the highest IDs.
    Images with `source_image = None` have a lower priority that images with a
    source image.

    :param predictions: The predictions to sort
    """
    return sorted(
        predictions,
        key=lambda prediction: (
            prediction.data.get("priority", 1),
            -int(get_image_id(prediction.source_image) or 0)
            if prediction.source_image
            else 0,
        ),
    )


def select_deepest_taxonomized_candidates(
    candidates: List[Prediction], taxonomy: Taxonomy
):
    """Filter predictions to only keep the deepest items in the taxonomy.

    For instance, for a list of category predictions, the prediction with
    `value_tag` 'en:meat' will be removed if a prediction with `value_tag`
    'en:pork' is in the `candidates` list.

    :param candidates: The list of candidates to filter
    :param taxonomy: The taxonomy to use
    """
    value_tags = set()

    for candidate in candidates:
        if candidate.value_tag is None:
            logger.warning(f"Unexpected None `value_tag` (candidate: {candidate})")
        else:
            value_tags.add(candidate.value_tag)

    nodes = [taxonomy[node] for node in value_tags if node in taxonomy]
    selected_node_ids = set(node.id for node in taxonomy.find_deepest_nodes(nodes))
    return [
        candidate
        for candidate in candidates
        if candidate.value_tag in selected_node_ids
    ]


class InsightImporter(metaclass=abc.ABCMeta):
    """Abstract class for all insight importers."""

    @staticmethod
    @abc.abstractmethod
    def get_type() -> InsightType:
        """Return the type of generated insights.

        This method must be implemented in subclasses."""
        pass

    @staticmethod
    @abc.abstractmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        """Return the prediction types that are necessary to generate the
        insight type.

        For most insight types a set of a single element will be returned, but
        more complex insight types require several prediction types.
        This method must be implemented in subclasses.
        """
        pass

    @classmethod
    def import_insights(
        cls,
        predictions: List[Prediction],
        server_domain: str,
        automatic: bool,
        product_store: DBProductStore,
    ) -> int:
        """Import insights, this is the main method.

        :return: the number of insights that were imported.
        """
        required_prediction_types = cls.get_required_prediction_types()
        for prediction in predictions:
            if prediction.type not in required_prediction_types:
                raise ValueError(f"unexpected prediction type: '{prediction.type}'")

        inserts = 0
        for to_create, to_delete in cls.generate_insights(
            predictions, server_domain, automatic, product_store
        ):
            if to_delete:
                to_delete_ids = [insight.id for insight in to_delete]
                logger.info(f"Deleting insight IDs: {[str(x) for x in to_delete_ids]}")
                ProductInsight.delete().where(
                    ProductInsight.id.in_(to_delete_ids)
                ).execute()
            if to_create:
                inserts += batch_insert(
                    ProductInsight,
                    (model_to_dict(insight) for insight in to_create),
                    50,
                )

        return inserts

    @classmethod
    def generate_insights(
        cls,
        predictions: List[Prediction],
        server_domain: str,
        automatic: bool,
        product_store: DBProductStore,
    ) -> Iterator[Tuple[List[ProductInsight], List[ProductInsight]]]:
        """Given a list of predictions, yield tuples of ProductInsight to
        create and delete.

        It calls the `generate_candidates` method, specific to each insight type
        (and implemented in sub-classes).
        """
        timestamp = datetime.datetime.utcnow()
        server_type = get_server_type(server_domain).name

        for barcode, group in itertools.groupby(
            sorted(predictions, key=operator.attrgetter("barcode")),
            operator.attrgetter("barcode"),
        ):
            product = product_store[barcode]
            references = get_existing_insight(cls.get_type(), barcode, server_domain)

            if product is None:
                logger.info(
                    f"Product {barcode} not found in DB, deleting existing insights"
                )
                if references:
                    yield [], references
                continue

            product_predictions = sort_predictions(group)
            candidates = [
                candidate
                for candidate in cls.generate_candidates(product, product_predictions)
                if is_valid_insight_image(product.images, candidate.source_image)
            ]
            for candidate in candidates:
                if candidate.automatic_processing is None:
                    logger.warning(
                        f"Insight with automatic_processing=None: {candidate.__data__}"
                    )

                if not is_trustworthy_insight_image(
                    product.images, candidate.source_image
                ):
                    # Don't process automatically if the insight image is not
                    # trustworthy (too old and not selected)
                    candidate.automatic_processing = False
                if candidate.data.get("is_annotation"):
                    username = candidate.data.get("username")
                    if username:
                        # logo annotation by a user
                        candidate.username = username
                    # Note: we could add vote annotation for anonymous user,
                    # but it should be done outside this loop. It's not yet implemented

            to_create, to_delete = cls.get_insight_update(candidates, references)

            for insight in to_create:
                if not automatic:
                    insight.automatic_processing = False
                cls.add_fields(insight, product, timestamp, server_domain, server_type)

            yield to_create, to_delete

    @classmethod
    @abc.abstractmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        """From a list of Predictions associated with a product, yield
        candidate ProductInsights for import.

        The types of all Predictions must be a subset of the required types
        available by calling `InsightImporter.get_required_prediction_types`.
        This method must be implemented in subclasses.

        :param product: The Product associated with the Predictions
        :param predictions: The list of predictions for the product of type
        :yield: candidate ProductInsight
        """
        pass

    @classmethod
    def get_insight_update(
        cls, candidates: List[ProductInsight], reference_insights: List[ProductInsight]
    ) -> Tuple[List[ProductInsight], List[ProductInsight]]:
        """Return a tuple containing:
        - a list of ProductInsight to import
        - a list of ProductInsight to delete

        :param candidates: candidate predictions
        :param reference_insights: existing insights of this type and product
        """
        to_create: List[ProductInsight] = []
        # Keep already annotated insights in DB
        to_keep_ids = set(
            reference.id
            for reference in reference_insights
            if reference.annotation is not None
        )
        for candidate in candidates:
            match = False
            for reference in reference_insights:
                if cls.is_conflicting_insight(candidate, reference):
                    # Candidate conflicts with existing insight, keeping
                    # existing insight and discarding candidate
                    to_keep_ids.add(reference.id)
                    match = True

            if not match:
                for selected in to_create:
                    if cls.is_conflicting_insight(candidate, selected):
                        # Don't import candidate if it conflicts with an
                        # already selected candidate
                        break
                else:
                    to_create.append(candidate)

        to_delete = [
            insight for insight in reference_insights if insight.id not in to_keep_ids
        ]
        return to_create, to_delete

    @classmethod
    @abc.abstractmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        """Return True if a candidate ProductInsight conflicts with an
        existing or another candidate insight, in which case the candidate
        insight won't be imported.

        :param candidate: The candidate ProductInsight to import
        :param reference: A ProductInsight, either another candidate or an
        insight that exists in DB
        """
        pass

    @staticmethod
    def add_fields(
        insight: ProductInsight,
        product: Product,
        timestamp: datetime.datetime,
        server_domain: str,
        server_type: str,
    ):
        """Add mandatory insight fields."""
        barcode = insight.barcode
        insight.reserved_barcode = is_reserved_barcode(barcode)
        insight.server_domain = server_domain
        insight.server_type = server_type
        insight.id = str(uuid.uuid4())
        insight.timestamp = timestamp
        insight.countries = product.countries_tags
        insight.brands = product.brands_tags
        insight.n_votes = 0

        if insight.automatic_processing:
            insight.process_after = timestamp + datetime.timedelta(
                minutes=settings.INSIGHT_AUTOMATIC_PROCESSING_WAIT
            )


class PackagerCodeInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packager_code

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.packager_code}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value == reference.value

    @staticmethod
    def is_prediction_valid(
        product: Product,
        emb_code: str,
    ) -> bool:
        return normalize_emb_code(emb_code) not in [
            normalize_emb_code(c) for c in product.emb_codes_tags
        ]

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        yield from (
            ProductInsight(**prediction.to_dict())
            for prediction in predictions
            if cls.is_prediction_valid(product, prediction.value)  # type: ignore
        )


class LabelInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.label

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.label}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag or cls.is_parent_label(
            candidate.value_tag, {reference.value_tag}  # type: ignore
        )

    @staticmethod
    def is_prediction_valid(product: Product, tag: str) -> bool:
        return not (
            tag in product.labels_tags
            or LabelInsightImporter.is_parent_label(tag, set(product.labels_tags))
        )

    @classmethod
    def is_parent_label(cls, tag: str, to_check_labels: Set[str]) -> bool:
        # Check that the predicted label is not a parent of a
        # current/already predicted label
        return get_taxonomy(InsightType.label.name).is_parent_of_any(
            tag, to_check_labels, raises=False
        )

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        candidates = [
            prediction
            for prediction in predictions
            if cls.is_prediction_valid(product, prediction.value_tag)  # type: ignore
        ]
        taxonomy = get_taxonomy(InsightType.label.name)
        for candidate in select_deepest_taxonomized_candidates(candidates, taxonomy):
            insight = ProductInsight(**candidate.to_dict())
            if insight.automatic_processing is None:
                insight.automatic_processing = (
                    candidate.value_tag in AUTHORIZED_LABELS_STORE.get()
                )
            yield insight


class CategoryImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.category

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.category}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag or cls.is_parent_category(
            candidate.value_tag, {reference.value_tag}  # type: ignore
        )

    @classmethod
    def is_parent_category(cls, category: str, to_check_categories: Set[str]):
        # Check that the predicted category is not a parent of a
        # current/already predicted category
        return get_taxonomy(InsightType.category.name).is_parent_of_any(
            category, to_check_categories, raises=False
        )

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        candidates = [
            prediction
            for prediction in predictions
            if cls.is_prediction_valid(product, prediction.value_tag)  # type: ignore
        ]
        taxonomy = get_taxonomy(InsightType.category.name)
        yield from (
            ProductInsight(**candidate.to_dict())
            for candidate in select_deepest_taxonomized_candidates(candidates, taxonomy)
        )

    @staticmethod
    def is_prediction_valid(
        product: Product,
        category: str,
    ) -> bool:
        # check whether this is new information or if the predicted category
        # is not a parent of a current/already predicted category
        return not (
            category in product.categories_tags
            or CategoryImporter.is_parent_category(
                category, set(product.categories_tags)
            )
        )


class ProductWeightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.product_weight

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.product_weight}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value == reference.value

    @staticmethod
    def group_by_subtype(predictions: List[Prediction]) -> Dict[str, List[Prediction]]:
        predictions_by_subtype: Dict[str, List[Prediction]] = {}

        for prediction in predictions:
            matcher_type = prediction.data["matcher_type"]
            predictions_by_subtype.setdefault(matcher_type, [])
            predictions_by_subtype[matcher_type].append(prediction)

        return predictions_by_subtype

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        if product.quantity is not None or not predictions:
            # Don't generate candidates if the product weight is already
            # specified or if there are no predictions
            return

        # Only generate a single prediction at a time.
        # Predictions are sorted by ascending priority, so the first
        # prediction is assumed to be the best one
        prediction = predictions[0]
        insights_by_subtype = cls.group_by_subtype(predictions)

        insight = ProductInsight(**prediction.to_dict())
        if (
            len(set(x.value for x in insights_by_subtype[insight.data["matcher_type"]]))
            > 1
        ) or insight.data.get("source") == "product_name":
            # Multiple candidates with the same subtype and value, or product
            # weight coming from the product name (less accurate that OCR data)
            # -> don't process automatically
            insight.automatic_processing = False

        yield insight


class ExpirationDateImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.expiration_date

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.expiration_date}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value == reference.value

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        if (product and product.expiration_date) or not predictions:
            return

        # expiration date values are formatted according to ISO 8601, so we
        # can sort them in descending order to get the most recent one
        prediction = sorted(
            predictions, key=operator.attrgetter("value"), reverse=True
        )[0]
        if any(prediction.value != other.value for other in predictions):
            prediction.automatic_processing = False
        yield ProductInsight(**prediction.to_dict())


class BrandInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.brand

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.brand}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag

    @staticmethod
    def is_valid(barcode: str, tag: str) -> bool:
        brand_prefix: Set[Tuple[str, str]] = BRAND_PREFIX_STORE.get()

        if not in_barcode_range(brand_prefix, tag, barcode):
            logger.info(f"Barcode {barcode} of brand {tag} not in barcode range")
            return False

        return True

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        if product.brands_tags:
            # For now, don't create an insight if a brand has already been provided
            return

        for prediction in predictions:
            if not cls.is_valid(product.barcode, prediction.value_tag):  # type: ignore
                continue
            insight = ProductInsight(**prediction.to_dict())
            if insight.automatic_processing is None:
                # Validation is needed if the weight was extracted from the product name
                # (not as trustworthy as OCR)
                insight.automatic_processing = (
                    prediction.data.get("source") == "product_name"
                )
            yield insight


class StoreInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.store

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.store}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        for prediction in predictions:
            insight = ProductInsight(**prediction.to_dict())
            insight.automatic_processing = True
            yield insight


class PackagingInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packaging

    @staticmethod
    def get_required_prediction_types() -> Set[PredictionType]:
        return {PredictionType.packaging}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        for prediction in predictions:
            insight = ProductInsight(**prediction.to_dict())
            insight.automatic_processing = True
            yield insight


def is_valid_product_prediction(
    prediction: Prediction, product: Optional[Product] = None
) -> bool:
    """Return True if the Prediction is valid and can be imported,
    i.e:
       - if the source image (if any) is valid
       - if the product was not deleted

    :param prediction: The Prediction to check
    :param product: The Product fetched from DBProductStore
    :return: Whether the Prediction is valid
    """
    if not product:
        # the product does not exist (deleted)
        logger.info(f"Prediction of deleted product {prediction.barcode}")
        return False

    if prediction.source_image and not is_valid_image(
        product.images, prediction.source_image
    ):
        logger.info(
            f"Invalid image for product {product.barcode}: {prediction.source_image}"
        )
        return False

    return True


def create_prediction_model(
    prediction: Prediction,
    server_domain: str,
    timestamp: datetime.datetime,
):
    return {
        "barcode": prediction.barcode,
        "type": prediction.type.name,
        "data": prediction.data,
        "timestamp": timestamp,
        "value_tag": prediction.value_tag,
        "value": prediction.value,
        "source_image": prediction.source_image,
        "automatic_processing": prediction.automatic_processing,
        "server_domain": server_domain,
        "predictor": prediction.predictor,
    }


def import_product_predictions(
    barcode: str,
    product_predictions_iter: Iterable[Prediction],
    server_domain: str,
):
    """Import predictions for a specific product.

    If a prediction already exists in DB (same (barcode, type, server_domain,
    source_image, value, value_tag)), it won't be imported.

    :param barcode: Barcode of the product. All `product_predictions` must
    have the same barcode.
    :param product_predictions_iter: Iterable of Predictions.
    :param server_domain: The server domain associated with the predictions.
    :return: The number of items imported in DB.
    """
    timestamp = datetime.datetime.utcnow()
    existing_predictions = set(
        PredictionModel.select(
            PredictionModel.type,
            PredictionModel.server_domain,
            PredictionModel.source_image,
            PredictionModel.value_tag,
            PredictionModel.value,
        )
        .where(PredictionModel.barcode == barcode)
        .tuples()
    )

    # note: there are some cases
    # when we could decide to replace old predictions of the same key.
    # It's not yet implemented.
    to_import = (
        create_prediction_model(prediction, server_domain, timestamp)
        for prediction in product_predictions_iter
        if (
            prediction.type,
            server_domain,
            prediction.source_image,
            prediction.value_tag,
            prediction.value,
        )
        not in existing_predictions
    )
    return batch_insert(PredictionModel, to_import, 50)


IMPORTERS: List[Type[InsightImporter]] = [
    PackagerCodeInsightImporter,
    LabelInsightImporter,
    CategoryImporter,
    ProductWeightImporter,
    ExpirationDateImporter,
    BrandInsightImporter,
    StoreInsightImporter,
    PackagingInsightImporter,
]


def import_insights(
    predictions: Iterable[Prediction],
    server_domain: str,
    automatic: bool,
    product_store: Optional[DBProductStore] = None,
) -> int:
    if product_store is None:
        product_store = get_product_store()

    updated_prediction_types_by_barcode = import_predictions(
        predictions, product_store, server_domain
    )
    return import_insights_for_products(
        updated_prediction_types_by_barcode, server_domain, automatic, product_store
    )


def import_insights_for_products(
    prediction_types_by_barcode: Dict[str, Set[PredictionType]],
    server_domain: str,
    automatic: bool,
    product_store: DBProductStore,
) -> int:
    """Re-compute insights for products with new predictions.

    :param prediction_types_by_barcode: a dict that associates each barcode
    with a set of prediction type that were updated
    :return: Number of imported insights
    """
    imported = 0
    for importer in IMPORTERS:
        required_prediction_types = importer.get_required_prediction_types()
        selected_barcodes: List[str] = []
        for barcode, prediction_types in prediction_types_by_barcode.items():
            if prediction_types >= required_prediction_types:
                selected_barcodes.append(barcode)

        if selected_barcodes:
            predictions = [
                Prediction(**p)
                for p in get_product_predictions(
                    selected_barcodes, list(required_prediction_types)
                )
            ]
            imported += importer.import_insights(
                predictions, server_domain, automatic, product_store
            )
    return imported


def import_predictions(
    predictions: Iterable[Prediction],
    product_store: DBProductStore,
    server_domain: str,
) -> Dict[str, Set[PredictionType]]:
    """Check validity and import provided Prediction.

    :param predictions: the Predictions to import
    :param product_store: The product store to use
    :param server_domain: The server domain associated with the predictions
    :return: Dict associating each barcode with prediction types that where
    updated in order to re-compute associated insights
    """
    predictions = [
        p
        for p in predictions
        if is_valid_product_prediction(p, product_store[p.barcode])  # type: ignore
    ]

    predictions_imported = 0
    updated_prediction_types_by_barcode: Dict[str, Set[PredictionType]] = {}
    for barcode, product_predictions_iter in itertools.groupby(
        sorted(predictions, key=operator.attrgetter("barcode")),
        operator.attrgetter("barcode"),
    ):
        product_predictions_group = list(product_predictions_iter)
        predictions_imported += import_product_predictions(
            barcode, product_predictions_group, server_domain
        )
        updated_prediction_types_by_barcode[barcode] = set(
            prediction.type for prediction in product_predictions_group
        )
    logger.info(f"{predictions_imported} predictions imported")
    return updated_prediction_types_by_barcode


def refresh_insights(
    barcode: str,
    server_domain: str,
    automatic: bool,
    product_store: Optional[DBProductStore] = None,
) -> int:
    """Refresh all insights for specific product.

    All predictions are fetched, and insights are created/deleted by each
    InsightImporter.

    This is different from `import_insights`, because here, there is no
    prediction creation.  It's just an refresh based on current database
    predictions. It's useful to refresh insights after an Product Opener
    update (some insights may be invalid).

    :param barcode: Barcode of the product.
    :param server_domain: The server domain associated with the predictions.
    :param automatic: If False, no insight is applied automatically.
    :param product_store: The product store to use, defaults to None
    :return: The number of imported insights.
    """
    if product_store is None:
        product_store = get_product_store()

    predictions = [Prediction(**p) for p in get_product_predictions([barcode])]
    prediction_types = set(p.type for p in predictions)

    imported = 0
    for importer in IMPORTERS:
        required_prediction_types = importer.get_required_prediction_types()
        if prediction_types >= required_prediction_types:
            imported += importer.import_insights(
                [p for p in predictions if p.type in required_prediction_types],
                server_domain,
                automatic,
                product_store,
            )

    return imported


def get_product_predictions(
    barcodes: List[str], prediction_types: Optional[List[str]] = None
) -> Iterator[Dict]:
    where_clauses = [PredictionModel.barcode.in_(barcodes)]

    if prediction_types is not None:
        where_clauses.append(PredictionModel.type.in_(prediction_types))

    yield from PredictionModel.select().where(*where_clauses).dicts().iterator()
