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
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
from robotoff.products import DBProductStore, Product, get_product_store, is_valid_image
from robotoff.taxonomy import Taxonomy, TaxonomyNode, get_taxonomy
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


def is_valid_insight_image(
    images: Dict[str, Any],
    source_image: Optional[str],
    max_timedelta: datetime.timedelta = settings.IMAGE_MAX_TIMEDELTA,
):
    """Return True if the source image is valid for insight generation:
      - the image ID is a digit and is referenced in `images`
      - the image is either selected or recent enough

    If `source_image` is None, we always consider the insight as valid.

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
            ProductInsight.id, ProductInsight.value, ProductInsight.value_tag
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
                ProductInsight.delete().where(
                    ProductInsight.id.in_([insight.id for insight in to_delete])
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

            product_predictions = sorted(
                group, key=lambda insight: insight.data.get("priority", 1)
            )
            candidates = [
                insight
                for insight in cls.generate_candidates(product, product_predictions)
                if is_valid_insight_image(product.images, insight.source_image)
            ]
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
        to_create = []
        to_keep_ids = set()
        for candidate in candidates:
            match = False
            for reference in reference_insights:
                if cls.is_conflicting_insight(candidate, reference):
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
            insight.process_after = timestamp + datetime.timedelta(minutes=10)


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
    def ignore_prediction(
        product: Product,
        emb_code: str,
    ) -> bool:
        return normalize_emb_code(emb_code) in [
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
            if not cls.ignore_prediction(product, prediction.value)  # type: ignore
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
    def ignore_prediction(product: Product, tag: str) -> bool:
        return tag in product.labels_tags or LabelInsightImporter.is_parent_label(
            tag, set(product.labels_tags)
        )

    @classmethod
    def is_parent_label(cls, tag: str, to_check_labels: Set[str]):
        # Check that the predicted label is not a parent of a
        # current/already predicted label
        label_taxonomy: Taxonomy = get_taxonomy(InsightType.label.name)

        if tag in label_taxonomy:
            label_node: TaxonomyNode = label_taxonomy[tag]

            for other_label_node in (
                label_taxonomy[to_check_label] for to_check_label in to_check_labels
            ):
                if other_label_node is not None and other_label_node.is_child_of(
                    label_node
                ):
                    return True

        return False

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        for prediction in predictions:
            if not cls.ignore_prediction(product, prediction.value_tag):  # type: ignore
                insight = ProductInsight(**prediction.to_dict())
                if insight.automatic_processing is None:
                    insight.automatic_processing = (
                        prediction.value_tag in AUTHORIZED_LABELS_STORE.get()
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
        category_taxonomy: Taxonomy = get_taxonomy(InsightType.category.name)

        if category in category_taxonomy:
            category_node: TaxonomyNode = category_taxonomy[category]

            for other_category_node in (
                category_taxonomy[to_check_category]
                for to_check_category in to_check_categories
            ):
                if other_category_node is not None and other_category_node.is_child_of(
                    category_node
                ):
                    return True

        return False

    @classmethod
    def generate_candidates(
        cls,
        product: Product,
        predictions: List[Prediction],
    ) -> Iterator[ProductInsight]:
        yield from (
            ProductInsight(**prediction.to_dict())
            for prediction in predictions
            if not cls.ignore_prediction(product, prediction.value_tag)  # type: ignore
        )

    @staticmethod
    def ignore_prediction(
        product: Product,
        category: str,
    ):
        # check whether this is new information or if the predicted category
        # is not a parent of a current/already predicted category
        return (
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
        if (product and product.quantity is not None) or not predictions:
            return

        insights_by_subtype = cls.group_by_subtype(predictions)
        insight_subtype = predictions[0].data["matcher_type"]
        prediction = predictions[0]

        insight = ProductInsight(**prediction.to_dict())
        if (
            insight_subtype != "with_mention"
            and len(insights_by_subtype[insight_subtype]) > 1
        ) or insight.data.get("source") == "product_name":
            # Multiple candidates, don't process automatically
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

        prediction = predictions[0]
        if len(set((prediction.value for prediction in predictions))):
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
            logger.warn(f"Barcode {barcode} of brand {tag} not in barcode range")
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


def is_valid_product_predictions(
    product_predictions: ProductPredictions, product: Optional[Product] = None
) -> bool:
    """Return True if the ProductPredictions is valid and can be imported,
    i.e:
       - if the source image (if any) is valid
       - if the product was not deleted

    :param product_predictions: The ProductPredictions to check
    :param product_store: The DBProductStore used to fetch the product
    information
    :return: Whether the ProductPredictions is valid
    """
    if not product:
        # the product does not exist (deleted)
        logger.info(f"Prediction of deleted product {product_predictions.barcode}")
        return False

    if product_predictions.source_image and not is_valid_image(
        product.images, product_predictions.source_image
    ):
        logger.info(
            f"Invalid image for product {product.barcode}: {product_predictions.source_image}"
        )
        return False

    return True


def create_prediction_model(
    prediction: Prediction,
    product_predictions: ProductPredictions,
    server_domain: str,
    timestamp: datetime.datetime,
):
    return {
        "barcode": product_predictions.barcode,
        "type": product_predictions.type.name,
        "data": prediction.data,
        "timestamp": timestamp,
        "value_tag": prediction.value_tag,
        "value": prediction.value,
        "source_image": product_predictions.source_image,
        "automatic_processing": prediction.automatic_processing,
        "server_domain": server_domain,
        "predictor": prediction.predictor,
    }


def import_product_predictions(
    barcode: str,
    product_predictions_iter: Iterable[ProductPredictions],
    server_domain: str,
):
    """Import product predictions.

    If a prediction already exists in DB (same (barcode, type, server_domain,
    source_image, value, value_tag)), it won't be imported.

    :param barcode: Barcode of the product. All `product_predictions` must
    have the same barcode.
    :param product_predictions_iter: Iterable of ProductPredictions.
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

    to_import = itertools.chain.from_iterable(
        (
            (
                create_prediction_model(
                    prediction, product_predictions, server_domain, timestamp
                )
                for prediction in product_predictions.predictions
                if (
                    product_predictions.type,
                    server_domain,
                    product_predictions.source_image,
                    prediction.value_tag,
                    prediction.value,
                )
                not in existing_predictions
            )
            for product_predictions in product_predictions_iter
        )
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
    product_predictions: Iterable[ProductPredictions],
    server_domain: str,
    automatic: bool,
    product_store: Optional[DBProductStore] = None,
) -> int:
    if product_store is None:
        product_store = get_product_store()

    updated_prediction_types_by_barcode = import_predictions(
        product_predictions, product_store, server_domain
    )
    return import_insights_for_products(
        updated_prediction_types_by_barcode, server_domain, automatic, product_store
    )


def import_insights_for_products(
    prediction_types_by_barcode: Dict[str, Set[PredictionType]],
    server_domain: str,
    automatic: bool,
    product_store: DBProductStore,
):
    imported = 0
    for importer in IMPORTERS:
        required_prediction_types = importer.get_required_prediction_types()
        for barcode, prediction_types in prediction_types_by_barcode.items():
            selected_barcodes: List[str] = []
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
    product_predictions: Iterable[ProductPredictions],
    product_store: DBProductStore,
    server_domain: str,
) -> Dict[str, Set[PredictionType]]:
    """Check validity and import provided ProductPredictions."""
    product_predictions = [
        p
        for p in product_predictions
        if is_valid_product_predictions(p, product_store[p.barcode])
    ]

    predictions_imported = 0
    updated_prediction_types_by_barcode: Dict[str, Set[PredictionType]] = {}
    for barcode, product_predictions_iter in itertools.groupby(
        sorted(product_predictions, key=operator.attrgetter("barcode")),
        operator.attrgetter("barcode"),
    ):
        product_predictions_group = list(product_predictions_iter)
        predictions_imported += import_product_predictions(
            barcode, product_predictions_group, server_domain
        )
        updated_prediction_types_by_barcode.setdefault(barcode, set())
        updated_prediction_types_by_barcode[barcode] |= set(
            itertools.chain.from_iterable(
                (prediction.type for prediction in x.predictions)
                for x in product_predictions_group
            )
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

    :param barcode: Barcode of the product.
    :param server_domain: The server domain associated with the predictions.
    :param automatic: If False, no insight is applied automatically.
    :param product_store: The product store to use, defaults to None
    :return: The number of imported insights.
    """
    if product_store is None:
        product_store = get_product_store()

    predictions = [Prediction(**p) for p in get_product_predictions([barcode])]

    imported = 0
    for importer in IMPORTERS:
        required_prediction_types = importer.get_required_prediction_types()
        if set(p.type for p in predictions) >= required_prediction_types:
            imported += importer.import_insights(
                predictions, server_domain, automatic, product_store
            )

    return imported


def get_product_predictions(
    barcodes: List[str], prediction_types: Optional[List[str]] = None
) -> Iterator[Dict]:
    where_clauses = [PredictionModel.barcode.in_(barcodes)]

    if prediction_types is not None:
        where_clauses.append(PredictionModel.type.in_(prediction_types))

    yield from PredictionModel.select().where(*where_clauses).dicts().iterator()
