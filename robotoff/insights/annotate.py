import abc

from robotoff.insights.enum import InsightType
from robotoff.models import ProductInsight, db, ProductIngredient
from robotoff.off import get_product, save_ingredients, add_emb_code
from robotoff.utils import get_logger

logger = get_logger(__name__)


class InsightAnnotator(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def annotate(self, insight: ProductInsight):
        pass


class PackagerCodeAnnotator(InsightAnnotator):
    def annotate(self, insight: ProductInsight):
        emb_code = insight.data['text']
        add_emb_code(insight.barcode, emb_code)


class IngredientSpellcheckAnnotator(InsightAnnotator):
    def annotate(self, insight: ProductInsight):
        barcode = insight.barcode

        try:
            product_ingredient: ProductIngredient = (ProductIngredient.select()
                                  .where(ProductIngredient.barcode == barcode).get())
        except ProductIngredient.DoesNotExist:
            logger.warning("Missing product ingredient for product {}".format(barcode))
            return

        ingredient_str = product_ingredient.ingredients
        product = get_product(barcode, fields=["ingredients_text"])

        if product is None:
            logger.warning("Missing product: {}".format(barcode))
            return

        expected_ingredients = product.get("ingredients_text")

        if expected_ingredients != ingredient_str:
            logger.warning("ingredients have changed since spellcheck insight creation "
                           "(product {})".format(barcode))
            return

        full_correction = self.generate_full_correction(ingredient_str,
                                                        insight.data['start_offset'],
                                                        insight.data['end_offset'],
                                                        insight.data['correction'])
        save_ingredients(barcode, full_correction)
        self.update_related_insights(insight)

        product_ingredient.ingredients = full_correction
        product_ingredient.save()

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
        return "{}{}{}".format(ingredient_str[start_offset-context_len:start_offset],
                               correction,
                               ingredient_str[end_offset:end_offset+context_len])

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


class InsightAnnotatorFactory:
    mapping = {
        InsightType.packager_code.name: PackagerCodeAnnotator,
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckAnnotator,
    }

    @classmethod
    def create(cls, identifier: str) -> InsightAnnotator:
        if identifier not in cls.mapping:
            raise ValueError("unknown annotator: {}".format(identifier))

        return cls.mapping[identifier]()
