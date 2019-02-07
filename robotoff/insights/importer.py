import abc
import uuid
from typing import Dict, Iterable, List, Optional, Any, Callable

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


def process_packaging_code_insight(insight: Dict[str, Any]) \
        -> Optional[Dict[str, Any]]:
    content = insight['content']

    return {
        'id': str(uuid.uuid4()),
        'type': insight['type'],
        'barcode': insight['barcode'],
        'data': {
            'source': insight['source'],
            'matcher_type': content['type'],
            'raw': content['raw'],
            'text': content['text'],
        }
    }


class OCRInsightProcessorFactory:
    processor_func = {
        InsightType.packager_code.name: process_packaging_code_insight,
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
        InsightType.packager_code.name: process_packaging_code_insight,
    }

    def import_insights(self, data: Iterable[Dict]):
        grouped_by: GroupedByOCRInsights = self.group_by_barcode(data)
        print(grouped_by)

        inserts = []

        for barcode, insights in grouped_by.items():
            for insight_type, insight_list in insights.items():
                processor_func = OCRInsightProcessorFactory.create(insight_type)

                if processor_func is None:
                    continue

                for insight in insight_list:
                    processed_insight = processor_func(insight)

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


class InsightImporterFactory:
    mapping = {
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckImporter,
        InsightType.packager_code.name: OCRInsightImporter,
    }

    @classmethod
    def create(cls, identifier: str) -> InsightImporter:
        if identifier not in cls.mapping:
            raise ValueError("unknown annotator: {}".format(identifier))

        return cls.mapping[identifier]()
