import abc
import datetime
from dataclasses import dataclass
from enum import Enum

from robotoff.insights._enum import InsightType
from robotoff.models import ProductInsight, db, ProductIngredient
from robotoff.off import get_product, save_ingredients, add_emb_code, \
    add_label_tag, add_category
from robotoff.utils import get_logger

logger = get_logger(__name__)


@dataclass
class AnnotationResult:
    status: str
    description: str = None


class AnnotationStatus(Enum):
    saved = 1
    updated = 2
    error_missing_product = 3
    error_updated_product = 4
    error_already_annotated = 5
    error_unknown_insight = 6


SAVED_ANNOTATION_RESULT = AnnotationResult(status=AnnotationStatus.saved.name,
                                           description="the annotation was saved")
UPDATED_ANNOTATION_RESULT = AnnotationResult(status=AnnotationStatus.updated.name,
                                             description="the annotation was saved and sent to OFF")
MISSING_PRODUCT_RESULT = AnnotationResult(status=AnnotationStatus.error_missing_product.name,
                                          description="the product could not be found on OFF")
ALREADY_ANNOTATED_RESULT = AnnotationResult(status=AnnotationStatus.error_already_annotated.name,
                                            description="the insight has already been annotated")
UNKNOWN_INSIGHT_RESULT = AnnotationResult(status=AnnotationStatus.error_unknown_insight.name,
                                          description="unknown insight ID")


class InsightAnnotator(metaclass=abc.ABCMeta):
    def annotate(self, insight: ProductInsight, annotation: int, update=True) \
            -> AnnotationResult:
        insight.annotation = annotation
        insight.completed_at = datetime.datetime.utcnow()
        insight.save()

        if annotation != 1:
            return SAVED_ANNOTATION_RESULT

        if update:
            return self.update_product(insight)

    @abc.abstractmethod
    def update_product(self, insight: ProductInsight) -> AnnotationResult:
        pass


class PackagerCodeAnnotator(InsightAnnotator):
    def update_product(self, insight: ProductInsight) -> AnnotationResult:
        emb_code = insight.data['text']
        add_emb_code(insight.barcode, emb_code)

        return UPDATED_ANNOTATION_RESULT


class LabelAnnotator(InsightAnnotator):
    def update_product(self, insight: ProductInsight) -> AnnotationResult:
        label_tag = insight.data['label_tag']
        add_label_tag(insight.barcode, label_tag)

        return UPDATED_ANNOTATION_RESULT


class IngredientSpellcheckAnnotator(InsightAnnotator):
    def update_product(self, insight: ProductInsight) -> AnnotationResult:
        barcode = insight.barcode

        try:
            product_ingredient: ProductIngredient = (
                ProductIngredient.select()
                                 .where(ProductIngredient.barcode == barcode)
                                 .get())
        except ProductIngredient.DoesNotExist:
            logger.warning("Missing product ingredient for product "
                           "{}".format(barcode))
            return AnnotationResult(status="error_no_matching_ingredient",
                                    description="no ingredient is associated "
                                                "with insight (internal error)")

        ingredient_str = product_ingredient.ingredients
        product = get_product(barcode, fields=["ingredients_text"])

        if product is None:
            logger.warning("Missing product: {}".format(barcode))
            return MISSING_PRODUCT_RESULT

        expected_ingredients = product.get("ingredients_text")

        if expected_ingredients != ingredient_str:
            logger.warning("ingredients have changed since spellcheck insight "
                           "creation (product {})".format(barcode))
            return AnnotationResult(status=AnnotationStatus
                                    .error_updated_product.name,
                                    description="the ingredient list has been "
                                                "updated since spellcheck")

        full_correction = self.generate_full_correction(
            ingredient_str,
            insight.data['start_offset'],
            insight.data['end_offset'],
            insight.data['correction'])
        save_ingredients(barcode, full_correction)
        self.update_related_insights(insight)

        product_ingredient.ingredients = full_correction
        product_ingredient.save()
        return UPDATED_ANNOTATION_RESULT

    @staticmethod
    def generate_full_correction(ingredient_str: str,
                                 start_offset: int,
                                 end_offset: int,
                                 correction: str):
        return "{}{}{}".format(ingredient_str[:start_offset],
                               correction,
                               ingredient_str[end_offset:])

    @staticmethod
    def generate_snippet(ingredient_str: str,
                         start_offset: int,
                         end_offset: int,
                         correction: str) -> str:
        context_len = 15
        return "{}{}{}".format(ingredient_str[start_offset-context_len:
                                              start_offset],
                               correction,
                               ingredient_str[end_offset:
                                              end_offset+context_len])

    @staticmethod
    def update_related_insights(insight: ProductInsight):
        diff_len = (len(insight.data['correction']) -
                    len(insight.data['original']))

        if diff_len == 0:
            return

        with db.atomic():
            for other in (ProductInsight.select()
                          .where(ProductInsight.barcode == insight.barcode,
                                 ProductInsight.id != insight.id,
                                 ProductInsight.type ==
                                 InsightType.ingredient_spellcheck.name)):
                if insight.data['start_offset'] <= other.data['start_offset']:
                    other.data['start_offset'] += diff_len
                    other.data['end_offset'] += diff_len
                    other.save()


class CategoryAnnotator(InsightAnnotator):
    def update_product(self, insight: ProductInsight) -> AnnotationResult:
        category_tag = insight.data['category']
        add_category(insight.barcode, category_tag)

        return UPDATED_ANNOTATION_RESULT


class InsightAnnotatorFactory:
    mapping = {
        InsightType.packager_code.name: PackagerCodeAnnotator(),
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckAnnotator(),
        InsightType.label.name: LabelAnnotator(),
        InsightType.category.name: CategoryAnnotator(),
    }

    @classmethod
    def get(cls, identifier: str) -> InsightAnnotator:
        if identifier not in cls.mapping:
            raise ValueError("unknown annotator: {}".format(identifier))

        return cls.mapping[identifier]
