import abc
import datetime
import itertools
import operator
import uuid
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional, Type, Union

from peewee import SQL
from playhouse.shortcuts import model_to_dict

from robotoff import settings
from robotoff.brands import get_brand_blacklist, get_brand_prefix, in_barcode_range
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import ImageModel, ImagePrediction
from robotoff.models import Prediction as PredictionModel
from robotoff.models import ProductInsight, batch_insert
from robotoff.prediction.ocr.packaging import SHAPE_ONLY_EXCLUDE_SET
from robotoff.products import (
    DBProductStore,
    Product,
    get_image_id,
    get_product_store,
    is_valid_image,
)
from robotoff.redis import Lock, LockedResourceException
from robotoff.taxonomy import (
    Taxonomy,
    TaxonomyType,
    get_taxonomy,
    match_taxonomized_value,
)
from robotoff.types import (
    InsightImportResult,
    InsightType,
    JSONType,
    NeuralCategoryClassifierModel,
    ObjectDetectionModel,
    PackagingElementProperty,
    Prediction,
    PredictionImportResult,
    PredictionType,
    ProductIdentifier,
    ProductInsightImportResult,
    ServerType,
)
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.cache import CachedStore

logger = get_logger(__name__)


def load_authorized_labels() -> set[str]:
    return set(text_file_iter(settings.OCR_LABEL_WHITELIST_DATA_PATH))


AUTHORIZED_LABELS_STORE = CachedStore(load_authorized_labels, expiration_interval=None)


def is_selected_image(images: dict[str, Any], image_id: str) -> bool:
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
    images: dict[str, Any], image_id: str, max_timedelta: datetime.timedelta
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
            logger.debug("More recent image: %s > %s", upload_datetime, image_datetime)
            return False

    return True


def is_valid_insight_image(image_ids: list[str], source_image: Optional[str]):
    """Return True if the source image is valid for insight generation,
    i.e. the image ID is a digit and is referenced in `images_ids`.

    If `source_image` is None, we always consider the insight as valid.

    :param image_ids: The list of existing image IDs for the product.
    :param source_image: The insight source image, should be the path of the
    image path or None.
    """
    if source_image is None:
        return True

    image_id = Path(source_image).stem
    return image_id.isdigit() and image_id in image_ids


def convert_bounding_box_absolute_to_relative(
    bounding_box_absolute: tuple[int, int, int, int],
    images: dict[str, Any],
    source_image: Optional[str],
) -> Optional[tuple[float, float, float, float]]:
    """Convert absolute bounding box coordinates to relative ones.

    When detecting patterns using regex or flashtext, we don't know the size of
    the image, so we cannot compute the relative coordinates of the text
    bounding box. We perform the conversion during insight import instead.

    Relative coordinates are used as they are more convenient than absolute ones
    (we can use them on a resized version of the original image).

    :param bounding_box_absolute: absolute coordinates of the bounding box
    :param images: The image dict as stored in MongoDB.
    :param source_image: The insight source image, should be the path of the
    image path or None.
    :return: a (y_min, x_min, y_max, x_max) tuple of the relative coordinates
        or None if a conversion error occured
    """
    if source_image is None:
        logger.warning(
            "could not convert absolute coordinate bounding box: "
            "bounding box was provided (%s) but source image is null",
            bounding_box_absolute,
        )
        return None

    image_id = Path(source_image).stem

    if image_id not in images:
        logger.info(
            "could not convert absolute coordinate bounding box: "
            "image %s not found in product images",
            image_id,
        )
        return None

    size = images[image_id]["sizes"]["full"]
    height = size["h"]
    width = size["w"]
    return (
        bounding_box_absolute[0] / height,
        bounding_box_absolute[1] / width,
        bounding_box_absolute[2] / height,
        bounding_box_absolute[3] / width,
    )


def get_existing_insight(
    insight_type: InsightType, product_id: ProductIdentifier
) -> list[ProductInsight]:
    """Get all insights for specific product and `insight_type`."""
    return list(
        ProductInsight.select().where(
            ProductInsight.type == insight_type.name,
            ProductInsight.barcode == product_id.barcode,
            ProductInsight.server_type == product_id.server_type.name,
        )
    )


def is_reserved_barcode(barcode: str) -> bool:
    if barcode.startswith("0"):
        barcode = barcode[1:]

    return barcode.startswith("2")


def sort_candidates(candidates: Iterable[ProductInsight]) -> list[ProductInsight]:
    """Sort candidates by priority, using as keys:

    - priority, specified by `data["priority"]`, candidate with lowest priority
      values (high priority) come first
    - source image upload datetime (most recent first): images IDs are
      auto-incremented integers, so the most recent images have the highest IDs.
      Images with `source_image = None` have a lower priority that images with a
      source image.
    - automatic processing status: candidates that are automatically
      processable have higher priority

    This function should be used to make sure most important candidates are
    looked into first in `get_insight_update`. Note that the sorting keys are
    a superset of those used in `InsightImporter.sort_predictions`.

    :param candidates: The candidates to sort
    :return: Sorted candidates
    """
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.data.get("priority", 1),
            -int(get_image_id(candidate.source_image) or 0)
            if candidate.source_image
            else 0,
            # automatically processable insights come first
            -int(candidate.automatic_processing),
            # hack to set a higher priority to prediction with a predictor value
            candidate.predictor or "z",
        ),
    )


def select_deepest_taxonomized_candidates(
    candidates: list[Prediction], taxonomy: Taxonomy
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
            logger.warning("Unexpected None `value_tag` (candidate: %s)", candidate)
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

    @classmethod
    @abc.abstractmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        """Return the prediction types that are necessary to generate
        insights.

        For most insight types a set of a single element will be returned, but
        more complex insight types require several prediction types.
        This method must be implemented in subclasses.
        """
        pass

    @classmethod
    def get_input_prediction_types(cls) -> set[PredictionType]:
        """Return the prediction types that are used as input to generate
        insights.

        By default it is the same as `get_required_prediction_types`
        but some insight types can use data from additional prediction types
        without it being required.

        This method can be subclassed is necessary.
        """
        return cls.get_required_prediction_types()

    @classmethod
    def import_insights(
        cls,
        product_id: ProductIdentifier,
        predictions: list[Prediction],
        product_store: DBProductStore,
    ) -> ProductInsightImportResult:
        """Import insights, this is the main method.

        :return: the number of insights that were imported.
        """
        input_prediction_types = cls.get_input_prediction_types()
        for prediction in predictions:
            if prediction.type not in input_prediction_types:
                raise ValueError(f"unexpected prediction type: '{prediction.type}'")

        if (
            len(
                prediction_barcodes := set(
                    prediction.barcode for prediction in predictions
                )
            )
            > 1
        ):
            raise ValueError(
                f"predictions for more than 1 product were provided: {prediction_barcodes}"
            )

        inserts = 0
        to_create, to_update, to_delete = cls.generate_insights(
            product_id, predictions, product_store
        )
        to_delete_ids = [insight.id for insight in to_delete]
        if to_delete_ids:
            ProductInsight.delete().where(
                ProductInsight.id.in_(to_delete_ids)
            ).execute()

        if to_create:
            inserts += batch_insert(
                ProductInsight,
                (model_to_dict(insight) for insight in to_create),
                50,
            )
        created_ids = [insight.id for insight in to_create]

        updated_ids = []
        for insight, reference_insight in to_update:
            update = {}
            for field_name in (
                key
                for key in insight.__data__.keys()
                if key not in ("id", "barcode", "type", "server_type")
            ):
                if getattr(insight, field_name) != getattr(
                    reference_insight, field_name
                ):
                    update[field_name] = getattr(insight, field_name)

            if update:
                updated_ids.append(reference_insight.id)
                ProductInsight.update(**update).where(
                    ProductInsight.id == reference_insight.id
                ).execute()

        return ProductInsightImportResult(
            insight_created_ids=created_ids,
            insight_deleted_ids=to_delete_ids,
            insight_updated_ids=updated_ids,
            product_id=product_id,
            type=cls.get_type(),
        )

    @classmethod
    def generate_insights(
        cls,
        product_id: ProductIdentifier,
        predictions: list[Prediction],
        product_store: DBProductStore,
    ) -> tuple[
        list[ProductInsight],
        list[tuple[ProductInsight, ProductInsight]],
        list[ProductInsight],
    ]:
        """Given a list of predictions, yield tuples of ProductInsight to
        create, update and delete.

        It calls the `generate_candidates` method, specific to each insight type
        (and implemented in sub-classes).
        """
        timestamp = datetime.datetime.utcnow()

        product = product_store[product_id]
        references = get_existing_insight(cls.get_type(), product_id)

        # If `ENABLE_PRODUCT_CHECK` is True (default, production settings), we
        # stop the import process and delete all associated insights
        if product is None and settings.ENABLE_PRODUCT_CHECK:
            logger.info("%s not found in DB, deleting existing insights", product_id)
            return [], [], references

        predictions = cls.sort_predictions(predictions)
        candidates = [
            candidate
            for candidate in cls.generate_candidates(product, predictions, product_id)
            # Don't check the image validity if product check was disabled (product=None)
            if product is None
            or is_valid_insight_image(product.image_ids, candidate.source_image)
        ]
        for candidate in candidates:
            if candidate.automatic_processing is None:
                logger.warning(
                    "Insight with automatic_processing=None: %s", candidate.__data__
                )
                candidate.automatic_processing = False

            # flashtext/regex insights return bounding boxes in absolute coordinates,
            # while we use relative coordinates elsewhere. Perform the conversion here.
            # Skip this step if product validity check is disabled (product=None),
            # as we don't have image information
            if (
                bounding_box_absolute := candidate.data.pop(
                    "bounding_box_absolute", None
                )
            ) is not None and product:
                candidate.data[
                    "bounding_box"
                ] = convert_bounding_box_absolute_to_relative(
                    bounding_box_absolute, product.images, candidate.source_image
                )

            if candidate.data.get("is_annotation"):
                username = candidate.data.get("username")
                if username:
                    # logo annotation by a user
                    candidate.username = username
                # Note: we could add vote annotation for anonymous user,
                # but it should be done outside this loop. It's not yet implemented

        to_create, to_update, to_delete = cls.get_insight_update(candidates, references)

        for insight in to_create:
            cls.add_fields(insight, product, timestamp)

        for insight, _ in to_update:
            cls.add_fields(insight, product, timestamp)

        return (to_create, to_update, to_delete)

    @classmethod
    def sort_predictions(cls, predictions: Iterable[Prediction]) -> list[Prediction]:
        """Sort predictions by priority, using as keys:
        - priority, specified by data["priority"], prediction with lowest priority
        values (high priority) come first
        - source image upload datetime (most recent first): images IDs are
        auto-incremented integers, so the most recent images have the highest IDs.
        Images with `source_image = None` have a lower priority that images with a
        source image.
        - predictor, predictions with predictor value have higher priority

        :param predictions: The predictions to sort
        :return: Sorted predictions
        """
        return sorted(
            predictions,
            key=lambda prediction: (
                prediction.data.get("priority", 1),
                -int(get_image_id(prediction.source_image) or 0)
                if prediction.source_image
                else 0,
                # hack to set a higher priority to prediction with a predictor value
                prediction.predictor or "z",
            ),
        )

    @classmethod
    @abc.abstractmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        """From a list of `Prediction`s associated with a product, yield
        candidate `ProductInsight`s for import.

        The types of all `Prediction`s must be a subset of the required types
        available by calling `InsightImporter.get_required_prediction_types`.
        This method must be implemented in subclasses.

        :param product: The Product associated with the Predictions, if null
            no validity check of the insight with respect to the product
            should be performed
        :param predictions: The list of predictions for the product of type
        :yield: candidate ProductInsight
        """
        pass

    @classmethod
    def get_insight_update(
        cls, candidates: list[ProductInsight], reference_insights: list[ProductInsight]
    ) -> tuple[
        list[ProductInsight],
        list[tuple[ProductInsight, ProductInsight]],
        list[ProductInsight],
    ]:
        """Return a tuple containing:

        - a list of `ProductInsight` to create
        - a list of `ProductInsight` to update, as (`insight`, `reference_insight`)
          tuples, where `insight` is the candidate and `reference_insight` is
          the insight already in DB
        - a list of `ProductInsight` to delete

        :param candidates: candidate predictions
        :param reference_insights: existing insights of this type and product
        """
        to_create_or_update: list[tuple[ProductInsight, Optional[ProductInsight]]] = []
        # Keep already annotated insights in DB
        to_keep_ids = set(
            reference.id
            for reference in reference_insights
            # Don't delete already annotated insights
            if reference.annotation is not None
            # Don't overwrite an insight that is going to be applied
            # automatically soon
            or reference.automatic_processing is True
        )
        for candidate in cls.sort_candidates(candidates):
            # if match is True, candidate conflicts with existing insight,
            # keeping existing insight and discarding candidate
            match = any(
                cls.is_conflicting_insight(candidate, reference_insight)
                for reference_insight in reference_insights
                if reference_insight.annotation is not None
                # Don't overwrite an insight that is going to be applied
                # automatically soon
                or reference_insight.automatic_processing is True
            )

            if not match:
                for selected, _ in to_create_or_update:
                    if cls.is_conflicting_insight(candidate, selected):
                        # Don't import candidate if it conflicts with an
                        # already selected candidate
                        break
                else:
                    mapping_ref_insight = None
                    # In order for the voting system to work, we map insights to create
                    # to existing insights with the same value/value_tag/source_image.
                    # This way, we don't loose vote information.
                    for reference_insight in reference_insights:
                        if (
                            reference_insight.annotation is None
                            and cls.is_conflicting_insight(candidate, reference_insight)
                            # only map to existing insight if the source image is the same,
                            # otherwise create a new insight
                            and candidate.source_image == reference_insight.source_image
                        ):
                            mapping_ref_insight = reference_insight
                            to_keep_ids.add(reference_insight.id)
                            break

                    # If mapping_ref_insight is None, a new insight is created in DB,
                    # Otherwise the reference insight is updated with candidate
                    # information
                    to_create_or_update.append((candidate, mapping_ref_insight))

        to_delete = [
            insight for insight in reference_insights if insight.id not in to_keep_ids
        ]
        to_create = [
            insight
            for insight, ref_insight in to_create_or_update
            if ref_insight is None
        ]
        to_update = [
            (insight, ref_insight)
            for insight, ref_insight in to_create_or_update
            if ref_insight is not None
        ]
        return to_create, to_update, to_delete

    @classmethod
    def sort_candidates(
        cls, candidates: Iterable[ProductInsight]
    ) -> list[ProductInsight]:
        """Sort candidates by priority, using as keys:

        - priority, specified by `data["priority"]`, candidate with lowest priority
        values (high priority) come first
        - source image upload datetime (most recent first): images IDs are
        auto-incremented integers, so the most recent images have the highest IDs.
        Images with `source_image = None` have a lower priority that images with a
        source image.
        - automatic processing status: candidates that are automatically
        processable have higher priority

        This function should be used to make sure most important candidates are
        looked into first in `get_insight_update`. Note that the sorting keys are
        a superset of those used in `InsightImporter.sort_predictions`.

        :param candidates: The candidates to sort
        :return: Sorted candidates
        """
        return sorted(
            candidates,
            key=lambda candidate: (
                candidate.data.get("priority", 1),
                (
                    -int(get_image_id(candidate.source_image) or 0)
                    if candidate.source_image
                    else 0
                ),
                # automatically processable insights come first
                -int(candidate.automatic_processing),
                # hack to set a higher priority to prediction with a predictor value
                candidate.predictor or "z",
            ),
        )

    @classmethod
    @abc.abstractmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        """Return `True` if a candidate `ProductInsight` conflicts with an
        existing or another candidate insight, in which case the candidate
        insight won't be imported.

        :param candidate: The candidate `ProductInsight` to import
        :param reference: A `ProductInsight`, either another candidate or an
        insight that exists in DB
        """
        pass

    @classmethod
    def add_fields(
        cls,
        insight: ProductInsight,
        product: Optional[Product],
        timestamp: datetime.datetime,
    ):
        """Add mandatory insight fields (`id`, `timestamp`,
        `automatic_processing`,...).

        :param insight: the insight to update
        :param product: the `Product` associated with the insight
        :param timestamp: insight creation datetime
        """
        barcode = insight.barcode
        insight.reserved_barcode = is_reserved_barcode(barcode)
        insight.id = str(uuid.uuid4())
        insight.timestamp = timestamp
        insight.n_votes = 0

        if product:
            insight.countries = product.countries_tags
            insight.brands = product.brands_tags
            insight.unique_scans_n = product.unique_scans_n

        if insight.automatic_processing:
            insight.process_after = timestamp + datetime.timedelta(
                minutes=settings.INSIGHT_AUTOMATIC_PROCESSING_WAIT
            )

        cls.add_optional_fields(insight, product)

    @classmethod
    def add_optional_fields(  # noqa: B027
        cls, insight: ProductInsight, product: Optional[Product]
    ):
        """Overwrite this method in children classes to add optional fields.

        The `campaign` field should be populated here.

        :param insight: the ProductInsight
        :param product: the associated Product
        """
        pass


class PackagerCodeInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packager_code

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.packager_code}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value == reference.value

    @staticmethod
    def is_prediction_valid(
        product: Optional[Product],
        emb_code: str,
    ) -> bool:
        if product is None:
            # Predictions are always valid when product check is disabled (product=None)
            return True
        existing_codes = [normalize_emb_code(c) for c in product.emb_codes_tags]
        normalized_code = normalize_emb_code(emb_code)

        return normalized_code not in existing_codes

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
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

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.label}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag or cls.is_parent_label(
            candidate.value_tag, {reference.value_tag}  # type: ignore
        )

    @staticmethod
    def is_prediction_valid(product: Optional[Product], tag: str) -> bool:
        if product is None:
            # Predictions are always valid when product check is disabled (product=None)
            return True
        return not (
            tag in product.labels_tags
            or LabelInsightImporter.is_parent_label(tag, set(product.labels_tags))
        )

    @classmethod
    def is_parent_label(cls, tag: str, to_check_labels: set[str]) -> bool:
        # Check that the predicted label is not a parent of a
        # current/already predicted label
        return get_taxonomy(InsightType.label.name).is_parent_of_any(
            tag, to_check_labels, raises=False
        )

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        candidates = [
            prediction
            for prediction in predictions
            if cls.is_prediction_valid(product, prediction.value_tag)  # type: ignore
        ]
        for candidate in candidates:
            if candidate.value_tag:
                # we normalize `value_tag` to the canonical taxonomy value
                # it helps to deal with internationalization
                # (`fr:sans-gluten` and `en:no-gluten` is the same tag)
                value_tag = match_taxonomized_value(
                    candidate.value_tag, TaxonomyType.label.name
                )
                if value_tag is not None:
                    candidate.value_tag = value_tag

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

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.category}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag or cls.is_parent_category(
            candidate.value_tag, {reference.value_tag}  # type: ignore
        )

    @classmethod
    def is_parent_category(cls, category: str, to_check_categories: set[str]) -> bool:
        # Check that the predicted category is not a parent of a
        # current/already predicted category
        return get_taxonomy(InsightType.category.name).is_parent_of_any(
            category, to_check_categories, raises=False
        )

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        candidates = [
            prediction
            for prediction in predictions
            if cls.is_prediction_valid(product, prediction.value_tag)  # type: ignore
        ]
        taxonomy = get_taxonomy(InsightType.category.name)

        # Make sure we yield candidates with `above_threshold=True` even if
        # there are candidates that are deepest in the category taxonomy
        yield from (
            ProductInsight(**candidate.to_dict())
            for candidate in select_deepest_taxonomized_candidates(candidates, taxonomy)
            if candidate.data.get("above_threshold") is True
        )
        yield from (
            ProductInsight(**candidate.to_dict())
            for candidate in select_deepest_taxonomized_candidates(candidates, taxonomy)
            if candidate.data.get("above_threshold", False) is False
        )

    @staticmethod
    def is_prediction_valid(
        product: Optional[Product],
        category: str,
    ) -> bool:
        if product is None:
            # Predictions are always valid when product check is disabled (product=None)
            return True
        # check whether this is new information or if the predicted category
        # is not a parent of a current/already predicted category
        return not (
            category in product.categories_tags
            or CategoryImporter.is_parent_category(
                category, set(product.categories_tags)
            )
        )

    @classmethod
    def add_optional_fields(cls, insight: ProductInsight, product: Optional[Product]):
        taxonomy = get_taxonomy(InsightType.category.name)
        campaigns = []
        if (
            insight.value_tag in taxonomy
            and "agribalyse_food_code" in taxonomy[insight.value_tag].additional_data
        ):
            # This category is linked to an agribalyse category, add it as a
            # campaign tag
            campaigns.append("agribalyse-category")

        if (
            insight.predictor == "neural"
            and insight.data.get("model_version")
            == NeuralCategoryClassifierModel.keras_image_embeddings_3_0.value
            and insight.data.get("above_threshold", False)
        ):
            # Add `v3-categorizer-automatic-processing` campaign to category
            # insights that will be applied automatically soon
            # (experimental phase)
            campaigns.append("v3-categorizer-automatic-processing")

        if product and not product.categories_tags:
            # Add a campaign to track products with no categories filled in
            campaigns.append("missing-category")

        insight.campaign = campaigns


class ProductWeightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.product_weight

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.product_weight}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value == reference.value

    @staticmethod
    def group_by_subtype(predictions: list[Prediction]) -> dict[str, list[Prediction]]:
        predictions_by_subtype: dict[str, list[Prediction]] = {}

        for prediction in predictions:
            matcher_type = prediction.data["matcher_type"]
            predictions_by_subtype.setdefault(matcher_type, [])
            predictions_by_subtype[matcher_type].append(prediction)

        return predictions_by_subtype

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        if (product and product.quantity is not None) or not predictions:
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

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.expiration_date}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value == reference.value

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
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

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.brand}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag

    @staticmethod
    def is_in_barcode_range(barcode: str, tag: str) -> bool:
        brand_prefix = get_brand_prefix()

        if not in_barcode_range(brand_prefix, tag, barcode):
            logger.info("Barcode %s of brand %s not in barcode range", barcode, tag)
            return False

        return True

    @staticmethod
    def is_prediction_valid(prediction: Prediction) -> bool:
        brand_blacklist = get_brand_blacklist()
        if prediction.value_tag in brand_blacklist:
            return False

        if (
            prediction.predictor == "universal-logo-detector"
            and "username" in prediction.data
        ):
            # Check barcode range for all predictors except logos detected using
            # universal-logo-detector model and annotated manually
            return True

        return BrandInsightImporter.is_in_barcode_range(
            prediction.barcode, prediction.value_tag  # type: ignore
        )

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        if product and product.brands_tags:
            # For now, don't create an insight if a brand has already been provided
            return

        for prediction in predictions:
            if not cls.is_prediction_valid(prediction):
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

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.store}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        return candidate.value_tag == reference.value_tag

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        for prediction in predictions:
            insight = ProductInsight(**prediction.to_dict())
            insight.automatic_processing = True
            yield insight


class NutritionImageImporter(InsightImporter):
    """Importer for nutrition image insight.

    This insight type predicts the nutrition image a product.
    """

    # Minimum number of nutrient mentions to have for an image to generate a
    # `nutrition_image` prediction
    MIN_NUM_NUTRIENT_MENTIONS = 4
    # Minimum number of nutrient values (ex: "15.5g" or "1525 kJ") to have for
    # an image to generate a `nutrition_image` prediction
    MIN_NUM_NUTRIENT_VALUES = 3
    # Minimum score for nutrition-table object detections to be considered
    # valid
    NUTRITION_TABLE_MODEL_MIN_SCORE = 0.9

    # Increase version ID when introducing breaking change: changes for which
    # we want old predictions to be removed in DB and replaced by newer ones
    PREDICTOR_VERSION = "1"

    @staticmethod
    def get_type() -> InsightType:
        return InsightType.nutrition_image

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.nutrient_mention, PredictionType.image_orientation}

    @classmethod
    def get_input_prediction_types(cls) -> set[PredictionType]:
        return {
            # `nutrient` is an optional prediction type
            PredictionType.nutrient,
            PredictionType.nutrient_mention,
            PredictionType.image_orientation,
        }

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        # `value_tag` contains the main language of the product
        return candidate.value_tag == reference.value_tag

    @staticmethod
    def sort_fn(prediction: Prediction) -> int:
        """Sort function used to group by source image in
        `generate_candidate`.

        Most recent images come first.
        """
        return -int(get_image_id(prediction.source_image or "") or 0)

    @classmethod
    def get_nutrition_table_predictions(
        cls, product_id: ProductIdentifier, min_score: float
    ) -> dict[str, list[JSONType]]:
        """Get all predictions made by the nutrition-table object detector
        model for `product_id`.

        Only objects of class `nutrition-table` and with `score >= min_score`
        are returned.

        :param product_id: identifier of the product
        :param min_score: minimum score of the detected object to be included.
        :return: a dict mapping `source_image` to a list of detected
            `nutrition-table` objects.
        """
        image_predictions = {}
        for data, source_image in (
            ImagePrediction.select(ImagePrediction.data, ImageModel.source_image)
            .join(ImageModel)
            .where(
                ImageModel.barcode == product_id.barcode,
                ImageModel.server_type == product_id.server_type.name,
                ImagePrediction.model_name
                == ObjectDetectionModel.nutrition_table.value,
                ImagePrediction.max_confidence >= min_score,
            )
            .tuples()
            .iterator()
        ):
            image_predictions[source_image] = [
                detected_object
                for detected_object in data["objects"]
                if detected_object["label"] == "nutrition-table"
                and detected_object["score"] >= min_score
            ]
        return image_predictions

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        # No prediction should have null source image, but filter just in case
        predictions = [p for p in predictions if p.source_image]
        # group by source image, by selecting newest images first
        predictions_by_source_image = [
            list(group)
            for _, group in itertools.groupby(
                sorted(predictions, key=cls.sort_fn),
                key=cls.sort_fn,
            )
        ]

        # Get all lang for which we already have a nutrition image
        existing_nutrition_image_langs = set(
            # image_key has the format `nutrition_fr`, get the lang by
            # splitting with '_' separator
            image_key.rsplit("_", maxsplit=1)[-1]
            for image_key in getattr(product, "images", {})
            if image_key.startswith("nutrition_")
        )
        logger.debug(
            "product %s has nutrition images for langs %s",
            product_id,
            existing_nutrition_image_langs,
        )
        nutrition_table_predictions = cls.get_nutrition_table_predictions(
            product_id, min_score=cls.NUTRITION_TABLE_MODEL_MIN_SCORE
        )
        logger.debug("nutrition table predictions: %s", nutrition_table_predictions)

        required_prediction_types = cls.get_required_prediction_types()
        for image_predictions in predictions_by_source_image:
            # We're not sure that for every `source_image` we have predictions
            # of all required types (we're only sure that we have predictions
            # of required types among predictions of all images)
            if set(p.type for p in image_predictions) < required_prediction_types:
                continue
            # `nutrient` prediction is optional, so the dict value associated
            # with `nutrient` PredictionType may be null
            image_prediction_by_type = {
                type_: [p for p in image_predictions if p.type == type_][0]
                if any(p for p in image_predictions if p.type == type_)
                else None
                for type_ in (
                    PredictionType.nutrient_mention,
                    PredictionType.nutrient,
                    PredictionType.image_orientation,
                )
            }
            # We ignore mypy warnings below because we necessarily have a
            # source image or predictions of the requested types
            source_image: str = image_predictions[0].source_image  # type: ignore
            logger.debug("Generating candidates for image: %s", source_image)
            for candidate in cls.generate_candidates_for_image(
                nutrient_mention_prediction=image_prediction_by_type[  # type: ignore
                    PredictionType.nutrient_mention
                ],
                image_orientation_prediction=image_prediction_by_type[  # type: ignore
                    PredictionType.image_orientation
                ],
                nutrient_prediction=image_prediction_by_type[PredictionType.nutrient],
                nutrition_table_predictions=nutrition_table_predictions.get(
                    source_image
                ),
            ):
                lang = candidate.value_tag
                logger.debug("One candidate generated for lang %s", lang)
                # Product is None if `ENABLE_PRODUCT_CHECK=False`, in which case we
                # always don't check that
                if product is None or (
                    # only select image for the product main language
                    lang == product.lang
                    # check that we don't already have a nutrition image for this lang
                    and lang not in existing_nutrition_image_langs
                ):
                    logger.debug(
                        "Candidate passed checks (nutrition mentions are in product main "
                        "language and no nutrition image is selected for main language)"
                    )
                    yield candidate

    @classmethod
    def generate_candidates_for_image(
        cls,
        nutrient_mention_prediction: Prediction,
        image_orientation_prediction: Prediction,
        nutrient_prediction: Optional[Prediction] = None,
        nutrition_table_predictions: Optional[list[JSONType]] = None,
    ) -> Iterator[ProductInsight]:
        """Generate `nutrition_image` candidates for a single image.

        :param nutrient_mention_prediction: the `Prediction` of type
            `nutrient_mention` for the image
        :param image_orientation_prediction: the `Prediction` of type
            `image_orientation` for the image
        :param nutrient_prediction: the `Prediction` of type
            `nutrient_prediction` for the image, optional
        :param nutrition_table_predictions: the list of detected
            `nutrition-table` objects, optional
        :yield: generated candidates
        """
        data: JSONType = {"priority": 1, "from_prediction_ids": {}}
        if nutrient_prediction is None:
            # If we don't detect nutrient mention + values, there are lower chances
            # that the image is a nutrition table, so we give it lower priority
            data["priority"] = 2
        else:
            # Save which nutrient prediction we used
            data["from_prediction_ids"]["nutrient"] = nutrient_prediction.id

        # Save which nutrient mention prediction we used
        data["from_prediction_ids"]["nutrient_mention"] = nutrient_mention_prediction.id
        mentioned_nutrients = nutrient_mention_prediction.data["mentions"]

        mention_by_lang: dict[str, set[str]] = {}
        for nutrient, nutrient_mention_items in mentioned_nutrients.items():
            if nutrient != "nutrient_value":
                for nutrient_mention in nutrient_mention_items:
                    for lang in nutrient_mention["languages"]:
                        mention_by_lang.setdefault(lang, set()).add(nutrient)

        # Get the rotation angle to apply when selecting the image, if the
        # original orientation is not correct
        data["rotation"] = image_orientation_prediction.data["rotation"]

        # Only add crop information if we detect a single `nutrition-table` object
        if nutrition_table_predictions and len(nutrition_table_predictions) == 1:
            nutrition_table_prediction = nutrition_table_predictions[0]
            data["bounding_box"] = nutrition_table_prediction["bounding_box"]
            data["crop_score"] = nutrition_table_prediction["score"]

        nutrient_values = mentioned_nutrients.get("nutrient_value", [])
        num_nutrient_values = len(nutrient_values)
        has_energy_nutrient_value = any(
            "kcal" in v["raw"].lower() or "kj" in v["raw"].lower()
            for v in nutrient_values
        )
        lang_nutrients = [
            (_lang, nutrients)
            for _lang, nutrients in mention_by_lang.items()
            # Over all possible nutrient mentions, we require to have at least
            # 4 of them to consider the image can be a nutrition images
            if len(nutrients) >= NutritionImageImporter.MIN_NUM_NUTRIENT_MENTIONS
            # We require to have at least 3 nutrient values (such as "15.5g"
            # or "1525 kJ") to consider the image can be a nutrition images
            and num_nutrient_values >= NutritionImageImporter.MIN_NUM_NUTRIENT_VALUES
            # We require to have energy values on the picture
            and has_energy_nutrient_value
        ]
        for lang, detected_nutrients in lang_nutrients:
            prediction = Prediction(
                type=PredictionType.nutrition_image,
                data={
                    **data,
                    "nutrients": list(detected_nutrients),
                },
                predictor_version=cls.PREDICTOR_VERSION,
                value_tag=lang,
                automatic_processing=False,
                barcode=nutrient_mention_prediction.barcode,
                server_type=nutrient_mention_prediction.server_type,
                source_image=nutrient_mention_prediction.source_image,
            )
            yield ProductInsight(**prediction.to_dict())


class PackagingElementTaxonomyException(Exception):
    pass


class PackagingImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packaging

    @classmethod
    def get_required_prediction_types(cls) -> set[PredictionType]:
        return {PredictionType.packaging}

    @classmethod
    def is_conflicting_insight(
        cls, candidate: ProductInsight, reference: ProductInsight
    ) -> bool:
        # Only keep one insight per element (=shape)
        return candidate.data["element"].get("shape", {}).get(
            "value_tag"
        ) == reference.data["element"].get("shape", {}).get("value_tag")

    @staticmethod
    def discard_packaging_element(
        candidate_element: dict,
        ref_element: dict,
        taxonomies: dict[str, Taxonomy],
    ):
        """Return True if `candidate_element` is a superset of `ref_element`.

        `ref_element` is a packaging element that is currently present on the
        product, `candidate_element` is a packaging element that was
        predicted. The purpose of this method is to discard predicted
        candidate elements that don't bring any information to the product.

        Examples:
        - candidate {shape: bottle} is uninformative if product already has an
          element {shape: bottle, material: plastic}
        - candidate {shape: bottle-cap, material: PET} is informative and
          should be kept even if product already has an element
          {shape: bottle-cap, material: plastic} (as plastic is a parent of
          PET in material taxonomy)
        """
        # normalize to be sure to have all needed keys
        for prop in PackagingElementProperty:
            candidate_element.setdefault(prop.value, None)
            ref_element.setdefault(prop.value, None)

        candidate_shape_is_parent_of_ref = False
        for prop_value, taxonomy in (
            (
                PackagingElementProperty.shape.value,
                taxonomies[TaxonomyType.packaging_shape.name],
            ),
            (
                PackagingElementProperty.material.value,
                taxonomies[TaxonomyType.packaging_material.name],
            ),
            (
                PackagingElementProperty.recycling.value,
                taxonomies[TaxonomyType.packaging_recycling.name],
            ),
        ):
            if candidate_element[prop_value]:
                if not ref_element[prop_value]:
                    # candidate has a property that reference doesn't have,
                    # so it cannot be a superset
                    return False

                candidate_node = taxonomy[candidate_element[prop_value]]
                ref_node = taxonomy[ref_element[prop_value]]

                if candidate_node is None:
                    logger.warning(
                        "packaging element %s not found", candidate_element[prop_value]
                    )
                    return True

                if ref_node is None:
                    # Reference value was not found in taxonomy, keep the
                    # candidate
                    return False

                if ref_node.is_parent_of(candidate_node):
                    return False

                if prop_value == PackagingElementProperty.shape.value:
                    candidate_shape_is_parent_of_ref = (
                        candidate_node.is_parent_of(ref_node)
                        or candidate_node.id == ref_node.id
                    )

        # if `candidate_shape_is_parent_of_ref` is True, the candidate shape
        # is the same or is a parent of the reference shape, and is not more
        # precise for any other property, so discard it
        return candidate_shape_is_parent_of_ref

    @staticmethod
    def keep_prediction(prediction: Prediction, product: Optional[Product]) -> bool:
        """element may contain the following properties:
        - shape
        - recycling
        - material

        Each property value is a dict containing the following properties:
        - `value` (non-null)
        - `value_tag` (may be null)
        """
        element = prediction.data["element"]
        if "shape" not in element:
            # If the prediction doesn't contain a shape, it's not informative
            # enough to generate an insight
            return False

        candidate_element = {
            prop: element[prop]["value_tag"] for prop in element.keys()
        }

        if candidate_element["shape"] in SHAPE_ONLY_EXCLUDE_SET and not (
            candidate_element.get("material") or candidate_element.get("recycling")
        ):
            # Double-check here that we don't import shape-only predictions
            # with excluded shapes
            return False

        taxonomies = {
            name: get_taxonomy(name)
            for name in (
                TaxonomyType.packaging_shape.name,
                TaxonomyType.packaging_material.name,
                TaxonomyType.packaging_recycling.name,
            )
        }

        if not product:
            # Predictions are always valid when product check is disabled (product=None)
            return True

        return not any(
            PackagingImporter.discard_packaging_element(
                candidate_element, existing_element, taxonomies
            )
            for existing_element in product.packagings
        )

    @staticmethod
    def _prediction_sort_fn(prediction: Union[Prediction, ProductInsight]) -> int:
        """We use the number of element as an approximation of how much
        informative the prediction is (eg. prioritize predictions with
        recycling, material and shape)."""
        return len(prediction.data["element"])

    @classmethod
    def sort_predictions(cls, predictions: Iterable[Prediction]) -> list[Prediction]:
        return sorted(predictions, key=cls._prediction_sort_fn, reverse=True)

    @classmethod
    def sort_candidates(
        cls, candidates: Iterable[ProductInsight]
    ) -> list[ProductInsight]:
        return sorted(candidates, key=cls._prediction_sort_fn, reverse=True)

    @classmethod
    def generate_candidates(
        cls,
        product: Optional[Product],
        predictions: list[Prediction],
        product_id: ProductIdentifier,
    ) -> Iterator[ProductInsight]:
        # 1 prediction = 1 packaging element
        for prediction in (
            prediction
            for prediction in predictions
            if cls.keep_prediction(prediction, product)
        ):
            yield ProductInsight(**prediction.to_dict())


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
        logger.info("Prediction of deleted product %s", prediction.barcode)
        return False

    if prediction.source_image and not is_valid_image(
        product.images, prediction.source_image
    ):
        logger.info(
            f"Invalid image for product {product.barcode}: {prediction.source_image}"
        )
        return False

    return True


def create_prediction_model(prediction: Prediction, timestamp: datetime.datetime):
    prediction_dict = prediction.to_dict()
    prediction_dict.pop("id")
    return {**prediction_dict, "timestamp": timestamp}


def _import_product_predictions_sort_fn(
    prediction: Prediction,
) -> tuple[ServerType, PredictionType, Optional[str], Optional[str]]:
    return (
        prediction.server_type,
        prediction.type,
        prediction.source_image,
        prediction.predictor_version,
    )


def import_product_predictions(
    barcode: str,
    server_type: ServerType,
    product_predictions: list[Prediction],
    delete_previous_versions: bool = True,
) -> tuple[int, int]:
    """Import predictions for a specific product.

    If a prediction already exists in DB (same (barcode, type,
    source_image, value, value_tag, predictor, automatic_processing)), it
    won't be imported.

    :param barcode: Barcode of the product. All `product_predictions` must
        have the same barcode.
    :param server_type: the server type (project) of the product, all
        `product_predictions` must have the same `server_type`.
    :param product_predictions: list of Predictions to import.
    :param delete_previous_versions: if True, delete predictions associated
        with the product that have different `predictor_version` than the one
        specified in `product_predictions`. Note that the deletion only affects
        the predictions of the same prediction type, server type, source image
        and barcode.
    :return: a (imported, deleted) tuple: the number of predictions imported
        and deleted in DB.
    """
    timestamp = datetime.datetime.utcnow()

    deleted = 0
    if delete_previous_versions:
        for (
            server_type,
            prediction_type,
            source_image,
            predictor_version,
        ), _ in itertools.groupby(
            sorted(product_predictions, key=_import_product_predictions_sort_fn),
            _import_product_predictions_sort_fn,
        ):
            deleted += (
                PredictionModel.delete()
                .where(
                    # Delete all predictions with the same barcode,
                    # server_type, source_image and type but with a different
                    # predictor_version
                    # We need a custom SQL query with 'IS DISTINCT FROM'
                    # as otherwise null values are considered specially when using
                    # standard '!=' operator
                    # See https://www.postgresql.org/docs/current/functions-comparison.html
                    SQL(
                        "prediction.barcode = %s AND "
                        "prediction.server_type = %s AND "
                        "prediction.type = %s AND "
                        "prediction.source_image = %s AND "
                        "prediction.predictor_version IS DISTINCT FROM %s",
                        (
                            barcode,
                            server_type.name,
                            prediction_type.name,
                            source_image,
                            predictor_version,
                        ),
                    ),
                )
                .execute()
            )

    existing_predictions = set(
        PredictionModel.select(
            PredictionModel.type,
            PredictionModel.server_type,
            PredictionModel.source_image,
            PredictionModel.value_tag,
            PredictionModel.value,
            PredictionModel.predictor,
            PredictionModel.automatic_processing,
        )
        .where(
            PredictionModel.barcode == barcode,
            PredictionModel.server_type == server_type.name,
        )
        .tuples()
    )
    to_import = (
        create_prediction_model(prediction, timestamp)
        for prediction in product_predictions
        if (
            prediction.type,
            prediction.server_type.name,
            prediction.source_image,
            prediction.value_tag,
            prediction.value,
            prediction.predictor,
            prediction.automatic_processing,
        )
        not in existing_predictions
    )
    return batch_insert(PredictionModel, to_import, 50), deleted


IMPORTERS: list[Type] = [
    PackagerCodeInsightImporter,
    LabelInsightImporter,
    CategoryImporter,
    ProductWeightImporter,
    ExpirationDateImporter,
    BrandInsightImporter,
    StoreInsightImporter,
    PackagingImporter,
    NutritionImageImporter,
]


def import_insights(
    predictions: Iterable[Prediction],
    server_type: ServerType,
    product_store: Optional[DBProductStore] = None,
) -> InsightImportResult:
    """Import predictions and generate (and import) insights from these
    predictions.

    :param predictions: an iterable of Predictions to import
    :param server_type: the server type (project) of the product
    :param product_store: a ProductStore to use, by defaults
        DBProductStore (MongoDB-based product store) is used.
    """
    if product_store is None:
        product_store = get_product_store(server_type)

    updated_prediction_types_by_barcode, prediction_import_results = import_predictions(
        predictions, product_store, server_type
    )
    product_insight_import_results = import_insights_for_products(
        updated_prediction_types_by_barcode, product_store, server_type
    )
    return InsightImportResult(
        product_insight_import_results=product_insight_import_results,
        prediction_import_results=prediction_import_results,
    )


def import_insights_for_products(
    prediction_types_by_barcode: dict[str, set[PredictionType]],
    product_store: DBProductStore,
    server_type: ServerType,
) -> list[ProductInsightImportResult]:
    """Re-compute insights for products with new predictions.

    :param prediction_types_by_barcode: a dict that associates each barcode
        with a set of prediction type that were updated
    :param product_store: The product store to use
    :param server_type: the server type (project) of the product

    :return: Number of imported insights
    """
    import_results = []
    for importer in IMPORTERS:
        required_prediction_types = importer.get_required_prediction_types()
        input_prediction_types = importer.get_input_prediction_types()
        selected_barcodes: list[str] = []
        for barcode, prediction_types in prediction_types_by_barcode.items():
            if prediction_types >= required_prediction_types:
                selected_barcodes.append(barcode)

        if selected_barcodes:
            predictions = [
                Prediction(**p)
                for p in get_product_predictions(
                    selected_barcodes, server_type, list(input_prediction_types)
                )
            ]

            for barcode, product_predictions in itertools.groupby(
                sorted(predictions, key=operator.attrgetter("barcode")),
                operator.attrgetter("barcode"),
            ):
                product_id = ProductIdentifier(barcode, server_type)
                try:
                    with Lock(
                        name=f"robotoff:import:{product_id.server_type.name}:{product_id.barcode}",
                        expire=300,
                        timeout=10,
                    ):
                        result = importer.import_insights(
                            product_id,
                            list(product_predictions),
                            product_store,
                        )
                        import_results.append(result)
                except LockedResourceException:
                    logger.info(
                        "Couldn't acquire insight import lock, skipping insight import for %s",
                        product_id,
                    )
                    continue
    return import_results


def import_predictions(
    predictions: Iterable[Prediction],
    product_store: DBProductStore,
    server_type: ServerType,
) -> tuple[dict[str, set[PredictionType]], list[PredictionImportResult]]:
    """Check validity and import provided Prediction.

    :param predictions: the Predictions to import
    :param product_store: The product store to use
    :return: dict associating each barcode with prediction types that where
    updated in order to re-compute associated insights
    """
    predictions = [
        p
        for p in predictions
        if (
            # If product validity check is disable, all predictions are valid
            not settings.ENABLE_PRODUCT_CHECK
            or is_valid_product_prediction(p, product_store[ProductIdentifier(p.barcode, server_type)])  # type: ignore
        )
    ]

    predictions_import_results = []
    updated_prediction_types_by_barcode: dict[str, set[PredictionType]] = {}
    for barcode, product_predictions_iter in itertools.groupby(
        sorted(predictions, key=operator.attrgetter("barcode")),
        operator.attrgetter("barcode"),
    ):
        product_predictions_group = list(product_predictions_iter)
        predictions_imported, predictions_deleted = import_product_predictions(
            barcode, server_type, product_predictions_group
        )
        predictions_import_results.append(
            PredictionImportResult(
                created=predictions_imported,
                deleted=predictions_deleted,
                barcode=barcode,
                server_type=server_type,
            )
        )
        updated_prediction_types_by_barcode[barcode] = set(
            prediction.type for prediction in product_predictions_group
        )
    return updated_prediction_types_by_barcode, predictions_import_results


def refresh_insights(
    product_id: ProductIdentifier,
    product_store: Optional[DBProductStore] = None,
) -> list[InsightImportResult]:
    """Refresh all insights for specific product.

    All predictions are fetched, and insights are created/deleted by each
    InsightImporter.

    This is different from `import_insights`, because here, there is no
    prediction creation.  It's just an refresh based on current database
    predictions. It's useful to refresh insights after an Product Opener
    update (some insights may be invalid).

    :param product_id: identifier of the product
    :param product_store: The product store to use, defaults to None
    :return: The number of imported insights.
    """
    if product_store is None:
        product_store = get_product_store(product_id.server_type)

    predictions = [
        Prediction(**p)
        for p in get_product_predictions([product_id.barcode], product_id.server_type)
    ]
    prediction_types = set(p.type for p in predictions)

    import_results = []
    for importer in IMPORTERS:
        required_prediction_types = importer.get_required_prediction_types()
        input_prediction_types = importer.get_input_prediction_types()
        if prediction_types >= required_prediction_types:
            import_result = importer.import_insights(
                product_id,
                [p for p in predictions if p.type in input_prediction_types],
                product_store,
            )
            import_results.append(import_result)
    return import_results


def get_product_predictions(
    barcodes: list[str],
    server_type: ServerType,
    prediction_types: Optional[list[str]] = None,
) -> Iterator[dict]:
    where_clauses = [
        PredictionModel.barcode.in_(barcodes),
        PredictionModel.server_type == server_type.name,
    ]

    if prediction_types is not None:
        where_clauses.append(PredictionModel.type.in_(prediction_types))

    yield from PredictionModel.select().where(*where_clauses).dicts().iterator()
