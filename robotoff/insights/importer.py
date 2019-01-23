import abc
import uuid
from typing import Dict, Iterable

from robotoff.insights.enum import InsightType
from robotoff.models import batch_insert, ProductInsight, ProductIngredient
from robotoff.utils import get_logger, jsonl_iter

logger = get_logger(__name__)


class InsightImporter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def import_insights(self, data: Iterable[Dict]):
        pass

    def from_jsonl(self, file_path):
        items = jsonl_iter(file_path)
        self.import_insights(items)


class IngredientSpellcheckImporter(InsightImporter):
    def import_insights(self, data: Iterable[Dict]):
        ProductInsight.delete().where(ProductInsight.type ==
                                      InsightType.ingredient_spellcheck.name).execute()
        ProductIngredient.delete().execute()

        barcode_seen = set()
        insight_seen = set()
        insights = []
        product_ingredients = []

        for item in data:
            barcode = item['barcode']
            corrections = item['corrections']
            text = item['text']

            if barcode not in barcode_seen:
                product_ingredients.append({
                    'barcode': barcode,
                    'ingredients': item['text'],
                })
                barcode_seen.add(barcode)

            for correction in corrections:
                start_offset = correction['start_offset']
                end_offset = correction['end_offset']
                key = (barcode, start_offset, end_offset)

                if key not in insight_seen:
                    original_snippet = self.generate_snippet(text,
                                                             start_offset, end_offset,
                                                             correction['original'])
                    corrected_snippet = self.generate_snippet(text,
                                                              start_offset, end_offset,
                                                              correction['correction'])
                    insights.append({
                        'id': str(uuid.uuid4()),
                        'type': InsightType.ingredient_spellcheck.name,
                        'barcode': barcode,
                        'data': {
                            **correction,
                            'original_snippet': original_snippet,
                            'corrected_snippet': corrected_snippet,
                        },
                    })
                    insight_seen.add(key)

            if len(product_ingredients) >= 50:
                batch_insert(ProductIngredient, product_ingredients, 50)
                product_ingredients = []

            if len(insights) >= 50:
                batch_insert(ProductInsight, insights, 50)
                insights = []

        batch_insert(ProductIngredient, product_ingredients, 50)
        batch_insert(ProductInsight, insights, 50)

    @staticmethod
    def generate_snippet(ingredient_str: str,
                         start_offset: int,
                         end_offset: int,
                         correction: str) -> str:
        context_len = 15
        return "{}{}{}".format(ingredient_str[start_offset-context_len:start_offset],
                               correction,
                               ingredient_str[end_offset:end_offset+context_len])


class InsightImporterFactory:
    mapping = {
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckImporter,
    }

    @classmethod
    def create(cls, identifier: str) -> InsightImporter:
        if identifier not in cls.mapping:
            raise ValueError("unknown annotator: {}".format(identifier))

        return cls.mapping[identifier]()
