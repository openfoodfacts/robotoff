import abc
import uuid
from typing import Dict, Iterable, List, Optional, Any, Callable

from robotoff.insights._enum import InsightType
from robotoff.models import batch_insert, ProductInsight, ProductIngredient
from robotoff.products import ProductStore
from robotoff.utils import get_logger, jsonl_iter, jsonl_iter_fp

logger = get_logger(__name__)


class InsightImporter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def import_insights(self, data: Iterable[Dict]):
        pass

    def from_jsonl(self, file_path):
        items = jsonl_iter(file_path)
        self.import_insights(items)

    def from_jsonl_fp(self, fp):
        items = jsonl_iter_fp(fp)
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


def get_emb_code_tag(emb_code: str) -> str:
    return (emb_code.lower()
                    .replace(' ', '-')
                    .replace('.', '-'))


def process_packager_code_insight(insight: Dict[str, Any], product_store: Optional[ProductStore]=None) \
        -> Optional[Dict[str, Any]]:
    barcode = insight['barcode']
    content = insight['content']

    if product_store:
        product = product_store[barcode]

        if not product:
            return

        emb_code_tag = get_emb_code_tag(content['text'])

        if emb_code_tag in product.emb_codes_tags:
            return

    return {
        'id': str(uuid.uuid4()),
        'type': insight['type'],
        'barcode': barcode,
        'data': {
            'source': insight['source'],
            'matcher_type': content['type'],
            'raw': content['raw'],
            'text': content['text'],
        }
    }


class OCRInsightProcessorFactory:
    processor_func = {
        InsightType.packager_code.name: process_packager_code_insight,
    }

    @classmethod
    def create(cls, key: str) -> Optional[Callable]:
        return cls.processor_func.get(key)


GroupedByOCRInsights = Dict[str, Dict[str, List]]


class OCRInsightImporter(InsightImporter):
    KEEP_TYPE = {
        InsightType.packager_code.name,
    }

    INSIGHT_PROCESSOR = {
        InsightType.packager_code.name: process_packager_code_insight,
    }

    def __init__(self, product_store: Optional[ProductStore]=None):
        self.product_store: ProductStore = product_store

    def import_insights(self, data: Iterable[Dict]):
        grouped_by: GroupedByOCRInsights = self.group_by_barcode(data)
        inserts = []

        for barcode, insights in grouped_by.items():
            for insight_type, insight_list in insights.items():
                ProductInsight.delete().where(ProductInsight.type == insight_type,
                                              ProductInsight.annotation.is_null()).execute()

                processor_func = OCRInsightProcessorFactory.create(insight_type)

                if processor_func is None:
                    continue

                for insight in insight_list:
                    processed_insight = processor_func(insight, self.product_store)

                    if processed_insight:
                        inserts.append(processed_insight)

        batch_insert(ProductInsight, inserts, 50)

    def group_by_barcode(self, data: Iterable[Dict]) -> GroupedByOCRInsights:
        grouped_by: GroupedByOCRInsights = {}

        for item in data:
            barcode = item['barcode']
            source = item['source']

            if not item['insights']:
                continue

            for insight_type, insights in item['insights'].items():
                if insight_type not in self.KEEP_TYPE:
                    continue

                grouped_by.setdefault(barcode, {})
                barcode_insights = grouped_by[barcode]
                barcode_insights.setdefault(insight_type, [])
                barcode_insights[insight_type] += [{
                    'source': source,
                    'barcode': barcode,
                    'type': insight_type,
                    'content': i,
                } for i in insights]

        return grouped_by
