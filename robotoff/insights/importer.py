import abc
import uuid
from typing import Dict, Iterable

from robotoff.models import batch_insert, ProductInsight, ProductIngredient
from robotoff.utils import get_logger, jsonl_iter

logger = get_logger(__name__)


class InsightImporter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def generate_insights(self, data: Iterable[Dict]) -> Iterable[Dict]:
        pass

    def from_jsonl(self, file_path):
        items = jsonl_iter(file_path)
        insights = self.generate_insights(items)
        batch_insert(ProductInsight, insights)


class IngredientSpellcheckImporter(InsightImporter):
    def generate_insights(self, data: Iterable[Dict]) -> Iterable[Dict]:
        barcode_seen = set()
        product_ingredients = []

        for item in data:
            barcode = item['barcode']
            corrections = item['corrections']

            if barcode not in barcode_seen:
                product_ingredients.append({
                    'barcode': barcode,
                    'ingredients': item['text'],
                })
                barcode_seen.add(barcode)

            for correction in corrections:
                yield {
                    'id': str(uuid.uuid4()),
                    'type': 'ingredient_spellcheck',
                    'barcode': barcode,
                    'data': correction,
                }

            if len(product_ingredients) >= 50:
                batch_insert(ProductIngredient, product_ingredients, 50)
                product_ingredients = []

        batch_insert(ProductIngredient, product_ingredients, 50)


class InsightImporterFactory:
    mapping = {
        'ingredient_spellcheck': IngredientSpellcheckImporter,
    }

    @classmethod
    def create(cls, identifier: str) -> InsightImporter:
        if identifier not in cls.mapping:
            raise ValueError("unknown annotator: {}".format(identifier))

        return cls.mapping[identifier]()
