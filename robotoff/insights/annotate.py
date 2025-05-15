"""This file allows to annotate insights, i.e. save the insight annotation
(`InsightAnnotation`) and send the update to Product Opener."""

import abc
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Type

from pydantic import ValidationError
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
    save_nutrients,
    select_rotate_image,
    unselect_image,
    update_emb_codes,
    update_expiration_date,
    update_quantity,
)
from robotoff.prediction.utils import get_image_rotation, get_nutrition_table_prediction
from robotoff.products import get_image_id, get_product
from robotoff.types import InsightAnnotation, InsightType, JSONType, NutrientData
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
    error_invalid_data = 11
    user_input_updated = 12
    cannot_vote = 13


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
USER_INPUT_UPDATED_ANNOTATION_RESULT = AnnotationResult(
    status_code=AnnotationStatus.user_input_updated.value,
    status=AnnotationStatus.user_input_updated.name,
    description="the data provided by the user was saved and sent to OFF",
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

INVALID_DATA = AnnotationResult(
    status_code=AnnotationStatus.error_invalid_data.value,
    status=AnnotationStatus.error_invalid_data.name,
    description="The data schema is invalid.",
)
CANNOT_VOTE_RESULT = AnnotationResult(
    status_code=AnnotationStatus.cannot_vote.value,
    status=AnnotationStatus.cannot_vote.name,
    description="The voting mechanism is not compatible with this insight type, please authenticate.",
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
        :param annotation: the annotation as an integer, either -1, 0, 1 or 2
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
        insight.completed_at = datetime.datetime.now(datetime.timezone.utc)

        if annotation in (1, 2) and update:
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
            AnnotationStatus.user_input_updated.value,
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

        user_input = False
        if data is None:
            category_tag = insight.value_tag
        else:
            value_tag = data.get("value_tag")
            if isinstance(value_tag, str):
                user_input = True
                category_tag = value_tag
            else:
                return AnnotationResult(
                    status_code=AnnotationStatus.error_invalid_data.value,
                    status=AnnotationStatus.error_invalid_data.name,
                    description="`data` is invalid, expected a single `value_tag` string field with the category tag",
                )

        if category_tag in categories_tags:
            return ALREADY_ANNOTATED_RESULT

        if user_input:
            insight.data["original_value_tag"] = insight.value_tag
            insight.data["user_input"] = True
            insight.value_tag = value_tag
            insight.value = None
            insight.save()

        add_category(
            product_id,
            category_tag,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return (
            USER_INPUT_UPDATED_ANNOTATION_RESULT
            if user_input
            else UPDATED_ANNOTATION_RESULT
        )


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


class UPCImageAnnotator(InsightAnnotator):
    """Annotator for UPC images.
    Unselect the selected images (front, nutrition, ingredients,...) for the
    product that match a UPC_Image. A UPC_Image is defined as an image that has
    a UPC (=barcode) with a high percentage area in the image and thus it is a
    poor selected photo.
    """

    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        product_id = insight.get_product_id()
        product = get_product(product_id, ["images"])

        image_id = get_image_id(insight.source_image or "")

        if product is None:
            logger.info(
                "Product %s not found, cannot unselect image %s", product_id, image_id
            )
            return MISSING_PRODUCT_RESULT

        images = product["images"]
        if image_id is None or image_id not in images:
            logger.info(
                "Image %s not found for product %s, cannot unselect",
                image_id,
                product_id,
            )
            return FAILED_UPDATE_RESULT
        to_unselect = []

        for image_field, image_data in (
            (key, data) for key, data in images.items() if not key.isdigit()
        ):
            if image_data["imgid"] == image_id:
                to_unselect.append(image_field)

        for image_field in to_unselect:
            logger.info(
                "Sending unselect request for image %s of %s", image_field, product_id
            )
            unselect_image(product_id, image_field, auth)

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

    :param bounding_box: relative bounding box coordinates (y_min, x_min,
        y_max, x_max)
    :param width: original height of the image
    :param height: original width of the image
    :param rotate: rotation angle (counter-clockwise) that we should apply to
        the bounding box, defaults to 0 (no rotation)
    :return: the converted bounding box coordinates
    """
    y_min, x_min, y_max, x_max = bounding_box
    crop_bounding_box = (
        y_min * height,
        x_min * width,
        y_max * height,
        x_max * width,
    )

    return rotate_bounding_box(
        crop_bounding_box,
        width,
        height,
        rotate=rotate,
    )


def rotate_bounding_box(
    bounding_box: tuple[float, float, float, float],
    width: int,
    height: int,
    rotate: int = 0,
) -> tuple[float, float, float, float]:
    """Rotate a bounding box based on the rotation angle.

    :param bounding_box: bounding box coordinates (y_min, x_min, y_max, x_max)
    :param width: width of the image
    :param height: height of the image
    :param rotate: rotation angle (counter-clockwise), defaults to 0
    :return: the rotated bounding box coordinates
    """
    if rotate == 90:
        # y_min = old_x_min
        # x_min = old_height - old_y_max
        # y_max = old_x_max
        # x_max = old_height - old_y_min
        bounding_box = (
            bounding_box[1],
            height - bounding_box[2],
            bounding_box[3],
            height - bounding_box[0],
        )
    if rotate == 180:
        # y_min = old_height - old_y_max
        # x_min = old_width - old_x_max
        # y_max = old_height - old_y_min
        # x_max = old_width - old_x_min
        bounding_box = (
            height - bounding_box[2],
            width - bounding_box[3],
            height - bounding_box[0],
            width - bounding_box[1],
        )
    if rotate == 270:
        # y_min = old_width - old_x_max
        # x_min = old_y_min
        # y_max = old_width - old_x_min
        # x_max = old_y_max
        bounding_box = (
            width - bounding_box[3],
            bounding_box[0],
            width - bounding_box[1],
            bounding_box[2],
        )
    return bounding_box


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

        image_key = f"nutrition_{insight.value_tag}"
        # We don't want to select the nutrition image if one has already been
        # selected
        if image_key in images:
            return ALREADY_ANNOTATED_RESULT

        rotation = insight.data.get("rotation", 0)
        crop_bounding_box: Optional[tuple[float, float, float, float]] = None
        if "bounding_box" in insight.data:
            # convert crop bounding box to the format expected by Product
            # Opener
            image_size = image_meta["sizes"]["full"]
            width = image_size["w"]
            height = image_size["h"]
            crop_bounding_box = convert_crop_bounding_box(
                insight.data["bounding_box"], width, height, rotation
            )

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


class IngredientSpellcheckAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        # Possibility for the annotator to change the spellcheck correction if data is
        # provided
        if data is not None:
            annotation = data.get("annotation")
            if not annotation or len(data) > 1:
                return INVALID_DATA
            # We add the new annotation to the Insight.
            json_data = insight.data
            json_data["annotation"] = annotation
            insight.data = json_data
            insight.save()

        ingredient_text = data.get("annotation") if data else insight.data["correction"]
        save_ingredients(
            product_id=insight.get_product_id(),
            ingredient_text=ingredient_text,
            lang=insight.value_tag,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        return UPDATED_ANNOTATION_RESULT


NUTRIENT_DEFAULT_UNIT = {
    "energy-kcal": "kcal",
    "energy-kj": "kJ",
    "proteins": "g",
    "carbohydrates": "g",
    "sugars": "g",
    "added-sugars": "g",
    "fat": "g",
    "saturated-fat": "g",
    "trans-fat": "g",
    "fiber": "g",
    "salt": "g",
    "iron": "mg",
    "sodium": "mg",
    "calcium": "mg",
    "potassium": "mg",
    "cholesterol": "mg",
    "vitamin-d": "µg",
}


class NutrientExtractionAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: dict | None = None,
        auth: OFFAuthentication | None = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        if is_vote:
            return CANNOT_VOTE_RESULT

        insight_updated = False
        # The annotator can change the nutrient values to fix the model errors
        if data is not None:
            try:
                validated_nutrients = cls.validate_data(data)
            except ValidationError as e:
                return AnnotationResult(
                    status_code=AnnotationStatus.error_invalid_data.value,
                    status=AnnotationStatus.error_invalid_data.name,
                    description=str(e),
                )
            validated_nutrients = cls.add_default_unit(validated_nutrients)
            # We override the predicted nutrient values by the ones submitted by the
            # user
            insight.data["annotation"] = validated_nutrients.model_dump()
            insight.data["was_updated"] = True
            insight_updated = True
        else:
            validated_nutrients = NutrientData.model_validate(insight.data)
            validated_nutrients = cls.add_default_unit(validated_nutrients)

            insight.data["annotation"] = validated_nutrients.model_dump()
            insight.data["was_updated"] = False
            insight_updated = True

        product_id = insight.get_product_id()
        product = get_product(product_id, ["code", "images", "lang"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        if insight_updated:
            insight.save()

        save_nutrients(
            product_id=product_id,
            nutrient_data=validated_nutrients,
            insight_id=insight.id,
            auth=auth,
            is_vote=is_vote,
        )
        cls.select_nutrition_image(insight, product, auth)
        return UPDATED_ANNOTATION_RESULT

    @classmethod
    def add_default_unit(cls, validated_nutrients: NutrientData) -> NutrientData:
        """Add default units to the nutrient values if unit is missing."""
        for nutrient_name, nutrient_value in validated_nutrients.nutrients.items():
            if nutrient_value.unit is None and nutrient_name in NUTRIENT_DEFAULT_UNIT:
                nutrient_value.unit = NUTRIENT_DEFAULT_UNIT[nutrient_name]
        return validated_nutrients

    @classmethod
    def validate_data(cls, data: JSONType) -> NutrientData:
        """Validate the `data` field submitted by the client.

        :params data: the data submitted by the client
        :return: the validated data

        :raises ValidationError: if the data is invalid
        """
        if "nutrients" not in data:
            raise ValidationError("missing 'nutrients' field")
        return NutrientData.model_validate(data)

    @classmethod
    def select_nutrition_image(
        cls,
        insight: ProductInsight,
        product: JSONType,
        auth: OFFAuthentication | None = None,
    ) -> None:
        """If the insight is validated, select the source image as nutrition image.

        We fetch the image orientation from the `predictions` table and the prediction
        of the nutrition table detector from the `image_predictions` table to know the
        rotation angle and the bounding box of the nutrition table.
        If any of these predictions are missing, we just select the image without any
        rotation or crop bounding box.

        :param insight: the original `nutrient_extraction` insight
        :param product: the product data
        :param auth: the user authentication data
        """

        if insight.source_image is None:
            return None

        image_id = get_image_id(insight.source_image)
        images = product.get("images", {})
        image_meta: JSONType | None = images.get(image_id)

        if not image_id or not image_meta:
            return None

        # Use the language of the product. This field should always be available,
        # but we provide a default value just in case.
        lang = product.get("lang", "en")
        image_key = f"nutrition_{lang}"
        # We don't want to select the nutrition image if the image is already
        # selected as nutrition image for the main language
        if image_key in images and images[image_key]["imgid"] == image_id:
            return None

        rotation = get_image_rotation(insight.source_image)

        nutrition_table_detections = get_nutrition_table_prediction(
            insight.source_image, threshold=0.5
        )
        bounding_box = None
        # Only crop according to the model predicted bounding box if there is exactly
        # one nutrition table detected
        if nutrition_table_detections and len(nutrition_table_detections) == 1:
            bounding_box = nutrition_table_detections[0]["bounding_box"]

        crop_bounding_box: tuple[float, float, float, float] | None = None
        if bounding_box:
            rotation = rotation or 0
            # convert crop bounding box to the format expected by Product
            # Opener
            image_size = image_meta["sizes"]["full"]
            width = image_size["w"]
            height = image_size["h"]
            crop_bounding_box = convert_crop_bounding_box(
                bounding_box, width, height, rotation
            )

        product_id = insight.get_product_id()
        select_rotate_image(
            product_id=product_id,
            image_id=image_id,
            image_key=image_key,
            rotate=rotation,
            crop_bounding_box=crop_bounding_box,
            auth=auth,
            is_vote=False,
            insight_id=insight.id,
        )


class ImageOrientationAnnotator(InsightAnnotator):
    @classmethod
    def process_annotation(
        cls,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        is_vote: bool = False,
    ) -> AnnotationResult:
        """Process image orientation annotation and rotate the selected image
        if necessary.

        :param insight: the image orientation insight
        :param data: additional data sent by the client, defaults to None
        :param auth: authentication data
        :param is_vote: True if the annotation was triggered by an anonymous
            vote, defaults to False
        :return: annotation result
        """
        product_id = insight.get_product_id()
        product = get_product(product_id, ["images"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        if insight.source_image is None:
            logger.warning(
                "Missing source_image in image orientation insight: %s", insight.id
            )
            return INVALID_DATA

        image_id = get_image_id(insight.source_image)

        if image_id is None:
            logger.warning(
                "Invalid image ID for image orientation insight: %s, %s",
                image_id,
                insight.id,
            )
            return INVALID_DATA

        rotation = insight.data.get("rotation")

        if rotation is None or rotation == 0:
            logger.warning(
                "Missing or zero rotation angle in image orientation insight: %s",
                insight.id,
            )
            return INVALID_DATA

        original_image_data = product["images"].get(image_id)
        if not original_image_data:
            logger.warning(
                "Original image %s not found in product images for insight: %s",
                image_id,
                insight.id,
            )
            return INVALID_DATA

        original_size = original_image_data.get("sizes", {}).get("full", {})
        original_height = original_size.get("h")
        original_width = original_size.get("w")

        if not original_height or not original_width:
            logger.warning(
                "Could not get original image dimensions for image %s, insight: %s",
                image_id,
                insight.id,
            )
            return INVALID_DATA

        # We'll check if the image is a selected image by iterating through
        # the product images looking for keys that indicate selected images
        selected_keys = []
        for key, image_data in product["images"].items():
            if key.startswith(("front", "ingredients", "nutrition", "packaging")):
                if image_data.get("imgid") == image_id:
                    selected_keys.append(key)

        if not selected_keys:
            logger.info(
                "Image %s is not a selected image, not applying rotation", image_id
            )
            return ALREADY_ANNOTATED_RESULT

        # Process all selected images that use this source image
        for selected_key in selected_keys:
            image_data = product["images"][selected_key]

            # Extract current crop information if it exists
            crop_bounding_box = None
            if all(k in image_data for k in ("x1", "y1", "x2", "y2")):
                # Check for uncropped images (coordinates = -1)
                if (
                    image_data["x1"] == "-1"
                    and image_data["y1"] == "-1"
                    and image_data["x2"] == "-1"
                    and image_data["y2"] == "-1"
                ):
                    pass
                else:
                    y1 = float(image_data["y1"])
                    x1 = float(image_data["x1"])
                    y2 = float(image_data["y2"])
                    x2 = float(image_data["x2"])

                    crop_bounding_box = rotate_bounding_box(
                        (y1, x1, y2, x2),
                        original_width,
                        original_height,
                        rotation,
                    )

            # Call the Product Opener API to rotate the image
            try:
                select_rotate_image(
                    product_id=product_id,
                    image_id=image_id,
                    image_key=selected_key,
                    rotate=rotation,
                    crop_bounding_box=crop_bounding_box,
                    auth=auth,
                    is_vote=is_vote,
                    insight_id=insight.id,
                )
            except Exception as e:
                logger.error("Error while rotating image %s: %s", image_id, str(e))
                return INVALID_DATA

        return UPDATED_ANNOTATION_RESULT


ANNOTATOR_MAPPING: dict[str, Type] = {
    InsightType.packager_code.name: PackagerCodeAnnotator,
    InsightType.label.name: LabelAnnotator,
    InsightType.category.name: CategoryAnnotator,
    InsightType.product_weight.name: ProductWeightAnnotator,
    InsightType.expiration_date.name: ExpirationDateAnnotator,
    InsightType.brand.name: BrandAnnotator,
    InsightType.store.name: StoreAnnotator,
    InsightType.packaging.name: PackagingAnnotator,
    InsightType.nutrition_image.name: NutritionImageAnnotator,
    InsightType.is_upc_image.name: UPCImageAnnotator,
    InsightType.ingredient_spellcheck.name: IngredientSpellcheckAnnotator,
    InsightType.nutrient_extraction: NutrientExtractionAnnotator,
    InsightType.image_orientation.name: ImageOrientationAnnotator,
}


def annotate(
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
    :param annotation: the annotation as an integer, either -1, 0, 1 or 2
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
    return ANNOTATOR_MAPPING[insight.type].annotate(
        insight=insight,
        annotation=annotation,
        update=update,
        data=data,
        auth=auth,
        is_vote=is_vote,
    )
