import abc
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from requests.exceptions import HTTPError, SSLError, Timeout

from robotoff.insights.dataclass import InsightType
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import ProductInsight, db
from robotoff.off import (
    OFFAuthentication,
    add_brand,
    add_category,
    add_label_tag,
    add_store,
    save_ingredients,
    select_rotate_image,
    update_emb_codes,
    update_expiration_date,
    update_quantity,
)
from robotoff.products import get_image_id, get_product
from robotoff.utils import get_logger

"""
This file allows to annotate products.

To check whether the annotation already exists or not (and save it and send it to the Open Food Facts database), use the following commands:
    from robotoff.insights.annotate import InsightAnnotatorFactor
    annotator = InsightAnnotatorFactory.get(insight_type)
    annotator.annotate(insight: ProductInsight, annotation: int, update: bool = True, data: Optional[dict] = None, auth: Optional[OFFAuthentication] = None, automatic: bool = False)

If you don't want to update the Open Food Facts database but only save the insight annotation (if the update is performed on the client side for example), you can call `annotate()` with `update=False`.
"""


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
    def annotate(
        self,
        insight: ProductInsight,
        annotation: int,
        update: bool = True,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        automatic: bool = False,
    ) -> AnnotationResult:
        with db.atomic() as tx:
            try:
                return self._annotate(
                    insight, annotation, update, data, auth, automatic
                )
            except HTTPError as e:
                if e.response.status_code >= 500:
                    logger.info("HTTPError occurred during OFF update: %s", e)
                    logger.info("Rolling back SQL transaction")
                    tx.rollback()
                    return FAILED_UPDATE_RESULT
                raise e
            except (Timeout, SSLError) as e:
                logger.info(
                    "Error occurred during OFF update: %s, %s", type(e).__name__, e
                )
                logger.info("Rolling back SQL transaction")
                tx.rollback()
                return FAILED_UPDATE_RESULT

    def _annotate(
        self,
        insight: ProductInsight,
        annotation: int,
        update: bool = True,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
        automatic: bool = False,
    ) -> AnnotationResult:
        if self.is_data_required() and data is None:
            return DATA_REQUIRED_RESULT

        username: Optional[str] = None
        if auth is not None:
            username = auth.get_username()

        insight.username = username
        insight.annotation = annotation
        insight.completed_at = datetime.datetime.utcnow()

        if automatic:
            insight.automatic_processing = True

        if annotation == 1 and update:
            # Save insight before processing the annotation
            insight.save()
            annotation_result = self.process_annotation(
                insight, data=data, auth=auth
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

    @abc.abstractmethod
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        pass

    def is_data_required(self) -> bool:
        return False


class PackagerCodeAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        emb_code: str = insight.value

        product = get_product(insight.barcode, ["emb_codes"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        emb_codes_str: str = product.get("emb_codes", "")

        emb_codes: list[str] = []
        if emb_codes_str:
            emb_codes = emb_codes_str.split(",")

        if self.already_exists(emb_code, emb_codes):
            return ALREADY_ANNOTATED_RESULT

        emb_codes.append(emb_code)
        update_emb_codes(
            insight.barcode,
            emb_codes,
            server_domain=insight.server_domain,
            insight_id=insight.id,
            auth=auth,
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
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        product = get_product(insight.barcode, ["labels_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        labels_tags: list[str] = product.get("labels_tags") or []

        if insight.value_tag in labels_tags:
            return ALREADY_ANNOTATED_RESULT

        add_label_tag(
            insight.barcode,
            insight.value_tag,
            insight_id=insight.id,
            server_domain=insight.server_domain,
            auth=auth,
        )
        return UPDATED_ANNOTATION_RESULT


class IngredientSpellcheckAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        barcode = insight.barcode
        lang = insight.data["lang"]
        field_name = "ingredients_text_{}".format(lang)
        product = get_product(barcode, [field_name])

        if product is None:
            return MISSING_PRODUCT_RESULT

        original_ingredients = insight.data["text"]
        corrected = insight.data["corrected"]
        expected_ingredients = product.get(field_name)

        if expected_ingredients != original_ingredients:
            logger.warning(
                "ingredients have changed since spellcheck insight "
                "creation (product %s)",
                barcode,
            )
            return AnnotationResult(
                status_code=AnnotationStatus.error_updated_product.value,
                status=AnnotationStatus.error_updated_product.name,
                description="the ingredient list has been updated since spellcheck",
            )

        save_ingredients(
            barcode,
            corrected,
            lang=lang,
            insight_id=insight.id,
            auth=auth,
        )
        return UPDATED_ANNOTATION_RESULT


class CategoryAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        product = get_product(insight.barcode, ["categories_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        categories_tags: list[str] = product.get("categories_tags") or []

        if insight.value_tag in categories_tags:
            return ALREADY_ANNOTATED_RESULT

        category_tag = insight.value_tag
        add_category(
            insight.barcode,
            category_tag,
            insight_id=insight.id,
            server_domain=insight.server_domain,
            auth=auth,
        )
        return UPDATED_ANNOTATION_RESULT


class ProductWeightAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        product = get_product(insight.barcode, ["quantity"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        quantity: Optional[str] = product.get("quantity") or None

        if quantity is not None:
            return ALREADY_ANNOTATED_RESULT

        update_quantity(
            insight.barcode,
            insight.value,
            insight_id=insight.id,
            server_domain=insight.server_domain,
            auth=auth,
        )
        return UPDATED_ANNOTATION_RESULT


class ExpirationDateAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        product = get_product(insight.barcode, ["expiration_date"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        current_expiration_date = product.get("expiration_date") or None

        if current_expiration_date:
            return ALREADY_ANNOTATED_RESULT

        update_expiration_date(
            insight.barcode,
            insight.value,
            insight_id=insight.id,
            server_domain=insight.server_domain,
            auth=auth,
        )
        return UPDATED_ANNOTATION_RESULT


class BrandAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        product = get_product(insight.barcode, ["brands_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        add_brand(
            insight.barcode,
            insight.value,
            insight_id=insight.id,
            server_domain=insight.server_domain,
            auth=auth,
        )

        return UPDATED_ANNOTATION_RESULT


class StoreAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        product = get_product(insight.barcode, ["stores_tags"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        stores_tags: list[str] = product.get("stores_tags") or []

        if insight.value_tag in stores_tags:
            return ALREADY_ANNOTATED_RESULT

        add_store(
            insight.barcode,
            insight.value,
            insight_id=insight.id,
            server_domain=insight.server_domain,
            auth=auth,
        )
        return UPDATED_ANNOTATION_RESULT


class NutritionImageAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        product = get_product(insight.barcode, ["code"])

        if product is None:
            return MISSING_PRODUCT_RESULT

        image_id = get_image_id(insight.source_image or "")

        if not image_id:
            return AnnotationResult(
                status_code=AnnotationStatus.error_invalid_image.value,
                status=AnnotationStatus.error_invalid_image.name,
                description="the image is invalid",
            )
        image_key = "nutrition_{}".format(insight.value_tag)
        select_rotate_image(
            barcode=insight.barcode,
            image_id=image_id,
            image_key=image_key,
            rotate=insight.data.get("rotation"),
            server_domain=insight.server_domain,
            auth=auth,
        )
        return UPDATED_ANNOTATION_RESULT


class NutritionTableStructureAnnotator(InsightAnnotator):
    def process_annotation(
        self,
        insight: ProductInsight,
        data: Optional[dict] = None,
        auth: Optional[OFFAuthentication] = None,
    ) -> AnnotationResult:
        insight.data["annotation"] = data
        insight.save()
        return SAVED_ANNOTATION_RESULT

    def is_data_required(self):
        return True


class InsightAnnotatorFactory:
    mapping = {
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckAnnotator(),
        InsightType.packager_code.name: PackagerCodeAnnotator(),
        InsightType.label.name: LabelAnnotator(),
        InsightType.category.name: CategoryAnnotator(),
        InsightType.product_weight.name: ProductWeightAnnotator(),
        InsightType.expiration_date.name: ExpirationDateAnnotator(),
        InsightType.brand.name: BrandAnnotator(),
        InsightType.store.name: StoreAnnotator(),
        InsightType.nutrition_image.name: NutritionImageAnnotator(),
        InsightType.nutrition_table_structure.name: NutritionTableStructureAnnotator(),
    }

    @classmethod
    def get(cls, identifier: str) -> InsightAnnotator:
        if identifier not in cls.mapping:
            raise ValueError("unknown annotator: {}".format(identifier))

        return cls.mapping[identifier]


class InvalidInsight(Exception):
    pass
