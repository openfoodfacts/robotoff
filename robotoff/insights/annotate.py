"""This file allows to annotate insights, i.e. save the insight annotation
(`InsightAnnotation`) and send the update to Product Opener."""

import abc
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Type

from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import HTTPError, SSLError, Timeout

from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import ProductInsight, db
from robotoff.off import (
    OFFAuthentication,
    add_brand,
    add_category,
    add_label_tag,
    add_packaging,
    add_store,
    save_ingredients,
    select_rotate_image,
    update_emb_codes,
    update_expiration_date,
    update_quantity,
)
from robotoff.products import get_image_id, get_product
from robotoff.types import InsightAnnotation, InsightType, JSONType
from robotoff.utils import get_logger

logger = get_logger(__name__)


@dataclass
class AnnotationResult:
    status_code: int
    status: str
    description: Optional[str] = None


class AnnotationStatus(Enum):
    saved = 1
    updated = 2
    error_missing_product = 3
    error_updated_product = 4
    error_already_annotated = 5
    error_unknown_insight = 6
    error_missing_data = 7
    error_invalid_image = 8
    vote_saved = 9
    error_failed_update = 10


SAVED_ANNOTATION_RESULT = AnnotationResult(
    status_code=AnnotationStatus.saved.value,
    status=AnnotationStatus.saved.name,
    description="the annotation was saved",
)
UPDATED_ANNOTATION_RESULT = AnnotationResult(
    status_code=AnnotationStatus.updated.value,
    status=AnnotationStatus.updated.name,
    description="the annotation was saved and sent to OFF",
)
MISSING_PRODUCT_RESULT = AnnotationResult(
    status_code=AnnotationStatus.error_missing_product.value,
    status=AnnotationStatus.error_missing_product.name,
    description="the product could not be found on OFF",
)
ALREADY_ANNOTATED_RESULT = AnnotationResult(
    status_code=AnnotationStatus.error_already_annotated.value,
    status=AnnotationStatus.error_already_annotated.name,
    description="the insight has already been annotated",
)
UNKNOWN_INSIGHT_RESULT = AnnotationResult(
    status_code=AnnotationStatus.error_unknown_insight.value,
    status=AnnotationStatus.error_unknown_insight.name,
    description="unknown insight ID",
)
DATA_REQUIRED_RESULT = AnnotationResult(
    status_code=AnnotationStatus.error_missing_data.value,
    status=AnnotationStatus.error_missing_data.name,
    description="annotation data is required as JSON in `data` field",
)
SAVED_ANNOTATION_VOTE_RESULT = AnnotationResult(
    status_code=AnnotationStatus.vote_saved.value,
    status=AnnotationStatus.vote_saved.name,
    description="the annotation vote was saved",
)
FAILED_UPDATE_RESULT = AnnotationResult(
    status_code=AnnotationStatus.error_failed_update.value,
    status=AnnotationStatus.error_failed_update.name,
    description="Open Food Facts update failed",
)


class InsightAnnotator(metaclass=abc.ABCMeta):
    @classmethod
    def annotate(
        cls,
        insight: ProductInsight,
        annotation: InsightAnnotation,
        update: bool = True,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        """Annotate an insight: save the annotation in DB and send the update
        to Product Opener if `update=True`.

        :param insight: the insight to annotate
        :param annotation: the annotation as an integer, either -1, 0 or 1
        :param update: if True, a write query is sent to Product Opener with
            the update, defaults to True
        :param data: additional data sent by the client, defaults to None
        :param auth: user authentication data, should be None if the
            annotation was triggered by an anonymous vote (in which case
            `is_vote=True`) or if the insight is applied automatically.
        :param is_vote: True if the annotation was triggered by an anonymous
            vote, defaults to False
        :return: the result of the annotation process
        """
        with db.atomic() as tx:
            try:
                return cls._annotate(insight, annotation, update, data, auth, is_vote)
            except HTTPError as e:
                if e.response.status_code >= 500:
                    logger.info(
                        "HTTPError occurred during OFF update: %s",
                        e.response.status_code,
                    )
                    logger.info("Rolling back SQL transaction")
                    tx.rollback()
                    return FAILED_UPDATE_RESULT
                raise e
            except (RequestConnectionError, Timeout, SSLError) as e:
                logger.info("Error occurred during OFF update", exc_info=e)
                logger.info("Rolling back SQL transaction")
                tx.rollback()
                return FAILED_UPDATE_RESULT

    @classmethod
    def _annotate(
        cls,
        insight: ProductInsight,
        annotation: InsightAnnotation,
        update: bool = True,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        if cls.is_data_required() and data is None:
            return DATA_REQUIRED_RESULT

        username: Optional[str] = None
        if auth is not None:
            username = auth.get_username()

        insight.username = username
        insight.annotation = annotation
        insight.completed_at = datetime.datetime.utcnow()

        if annotation == 1 and update:
            # Save insight before processing the annotation
            insight.save()
            annotation_result = cls.process_annotation(
                insight, data=data, auth=auth, is_vote=is_vote
            )  # calls the process_annotation function of the class corresponding to the current insight type
        else:
            annotation_result = SAVED_ANNOTATION_RESULT

        if annotation_result.status_code in (
            AnnotationStatus.saved.value,
            AnnotationStatus.updated.value,
            AnnotationStatus.error_invalid_image.value,
            AnnotationStatus.error_missing_product.value,
            AnnotationStatus.error_updated_product.value,
        ):
            insight.annotated_result = annotation_result.status_code
            insight.save()

        return annotation_result

    @classmethod
    @abc.abstractmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        pass

    @classmethod
    def is_data_required(cls) -> bool:
        return False


class PackagerCodeAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        emb_code: str = insight.value

        product_id = insight.get_product_id()
        product = get_product(product_id, ["emb_codes"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        emb_codes_str: str = product.get("emb_codes", "")

        emb_codes: list[str] = []
        if emb_codes_str:
            emb_codes = emb_codes_str.split(",")

        if cls.already_exists(emb_code, emb_codes):
            return ALREADY_ANNOTATED_RESULT

        emb_codes.append(emb_code)
        update_emb_codes(
            product_id,
            emb_codes,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT

    @staticmethod
    def already_exists(new_emb_code: str, emb_codes: list[str]) -> bool:
        emb_codes = [normalize_emb_code(emb_code) for emb_code in emb_codes]

        normalized_emb_code = normalize_emb_code(new_emb_code)

        if normalized_emb_code in emb_codes:
            return True

        return False


class LabelAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["labels_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        labels_tags: list[str] = product.get("labels_tags") or []

        if insight.value_tag in labels_tags:
            return ALREADY_ANNOTATED_RESULT

        add_label_tag(
            product_id,
            insight.value_tag,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


class IngredientSpellcheckAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        lang = insight.data["lang"]
        field_name = "ingredients_text_{}".format(lang)
        product = get_product(product_id, [field_name])

        if product is None:
            return MISSING_PRODUCT_RESULT

        original_ingredients = insight.data["text"]
        corrected = insight.data["corrected"]
        expected_ingredients = product.get(field_name)

        if expected_ingredients != original_ingredients:
            logger.warning(
                "ingredients have changed since spellcheck insight " "creation (%s)",
                product_id,
            )
            return AnnotationResult(
                status_code=AnnotationStatus.error_updated_product.value,
                status=AnnotationStatus.error_updated_product.name,
                description="the ingredient list has been updated since spellcheck",
            )

        save_ingredients(
            product_id,
            corrected,
            lang=lang,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


class CategoryAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["categories_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        categories_tags: list[str] = product.get("categories_tags") or []

        if insight.value_tag in categories_tags:
            return ALREADY_ANNOTATED_RESULT

        category_tag = insight.value_tag
        add_category(
            product_id,
            category_tag,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


class ProductWeightAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["quantity"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        quantity: Optional[str] = product.get("quantity") or None

        if quantity is not None:
            return ALREADY_ANNOTATED_RESULT

        update_quantity(
            product_id,
            insight.value,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


class ExpirationDateAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["expiration_date"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        current_expiration_date = product.get("expiration_date") or None

        if current_expiration_date:
            return ALREADY_ANNOTATED_RESULT

        update_expiration_date(
            product_id,
            insight.value,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


class BrandAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["brands_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        add_brand(
            product_id,
            insight.value,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )

        return UPDATED_ANNOTATION_RESULT


class StoreAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["stores_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        stores_tags: list[str] = product.get("stores_tags") or []

        if insight.value_tag in stores_tags:
            return ALREADY_ANNOTATED_RESULT

        add_store(
            product_id,
            insight.value,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


class PackagingAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["code"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        add_packaging(
            product_id,
            insight.data["element"],
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


def convert_crop_bounding_box(
    bounding_box: tuple[float, float, float, float],
    width: int,
    height: int,
    rotate: int = 0,
) -> tuple[float, float, float, float]:
    """Convert crop bounding box to the format expected by Product Opener:

    - convert relative to absolute coordinates
    - rotate the bounding box using the same angle as the selected image
      rotation angle

    :param bounding_box: relative bounding box coordinates (y_min, x_min, y_max, x_max)
    :param width: original height of the image
    :param height: original width of the image
    :param rotate: rotation angle that we should apply to the bounding box,
        defaults to 0 (no rotation)
    :return: the converted bounding box coordinates
    """
    y_min, x_min, y_max, x_max = bounding_box
    crop_bounding_box = (
        y_min * height,
        x_min * width,
        y_max * height,
        x_max * width,
    )

    if rotate == 90:
        # y_min = old_x_min
        # x_min = old_height - old_y_max
        # y_max = old_x_max
        # x_max = old_height - old_y_min
        crop_bounding_box = (
            crop_bounding_box[1],
            height - crop_bounding_box[2],
            crop_bounding_box[3],
            height - crop_bounding_box[0],
        )
    if rotate == 180:
        # y_min = old_height - old_y_max
        # x_min = old_width - old_x_max
        # y_max = old_height - old_y_min
        # x_max = old_width - old_x_min
        crop_bounding_box = (
            height - crop_bounding_box[2],
            width - crop_bounding_box[3],
            height - crop_bounding_box[0],
            width - crop_bounding_box[1],
        )
    if rotate == 270:
        # y_min = old_width - old_x_max
        # x_min = old_y_min
        # y_max = old_width - old_x_min
        # x_max = old_y_max
        crop_bounding_box = (
            width - crop_bounding_box[3],
            crop_bounding_box[0],
            width - crop_bounding_box[1],
            crop_bounding_box[2],
        )

    return crop_bounding_box


class NutritionImageAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["code", "images"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        image_id = get_image_id(insight.source_image or "")
        images = product.get("images", {})
        image_meta: Optional[JSONType] = images.get(image_id)

        if not image_id or not image_meta:
            return AnnotationResult(
                status_code=AnnotationStatus.error_invalid_image.value,
                status=AnnotationStatus.error_invalid_image.name,
                description="the image is invalid",
            )

        rotation = insight.data.get("rotation", 0)
        crop_bounding_box: Optional[tuple[float, float, float, float]] = None
        if "bounding_box" in insight.data:
            # convert crop bounding box to the format expected by Product Opener
            image_size = image_meta["sizes"]["full"]
            width = image_size["w"]
            height = image_size["h"]
            crop_bounding_box = convert_crop_bounding_box(
                insight.data["bounding_box"], width, height, rotation
            )

        image_key = f"nutrition_{insight.value_tag}"
        select_rotate_image(
            product_id=product_id,
            image_id=image_id,
            image_key=image_key,
            rotate=rotation,
            crop_bounding_box=crop_bounding_box,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


class NutritionTableStructureAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        insight.data["annotation"] = data
        insight.save()
        return SAVED_ANNOTATION_RESULT

    def is_data_required(self):
        return True


ANNOTATOR_MAPPING: dict[str, Type] = {
    InsightType.ingredient_spellcheck.name: IngredientSpellcheckAnnotator,
    InsightType.packager_code.name: PackagerCodeAnnotator,
    InsightType.label.name: LabelAnnotator,
    InsightType.category.name: CategoryAnnotator,
    InsightType.product_weight.name: ProductWeightAnnotator,
    InsightType.expiration_date.name: ExpirationDateAnnotator,
    InsightType.brand.name: BrandAnnotator,
    InsightType.store.name: StoreAnnotator,
    InsightType.packaging.name: PackagingAnnotator,
    InsightType.nutrition_image.name: NutritionImageAnnotator,
    InsightType.nutrition_table_structure.name: NutritionTableStructureAnnotator,
}


def annotate(
    insight: ProductInsight,
    annotation: InsightAnnotation,
    update: bool = True,
    data: Optional[dict] = None,
    auth: Optional[OFFAuthentication] = None,
    is_vote: bool = False,
) -> AnnotationResult:
    return ANNOTATOR_MAPPING[insight.type].annotate(
        insight=insight,
        annotation=annotation,
        update=update,
        data=data,
        auth=auth,
        is_vote=is_vote,
    )


class InvalidInsight(Exception):
    pass
