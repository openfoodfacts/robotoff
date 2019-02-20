import abc
import uuid
from typing import Dict, Iterable, List, Set, Optional

from robotoff.insights._enum import InsightType
from robotoff.insights.data import AUTHORIZED_LABELS
from robotoff.models import batch_insert, ProductInsight, ProductIngredient
from robotoff.products import ProductStore
from robotoff.utils import get_logger, jsonl_iter, jsonl_iter_fp
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


class InsightImporter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def import_insights(self, data: Iterable[Dict], purge: bool = False):
        pass

    @abc.abstractmethod
    def get_type(self) -> str:
        pass

    @abc.abstractmethod
    def need_product_store(self) -> bool:
        pass

    def from_jsonl(self, file_path):
        items = jsonl_iter(file_path)
        self.import_insights(items)

    def from_jsonl_fp(self, fp):
        items = jsonl_iter_fp(fp)
        self.import_insights(items)

    def need_validation(self, insight: ProductInsight) -> bool:
        return True


class IngredientSpellcheckImporter(InsightImporter):
    def get_type(self) -> str:
        return InsightType.ingredient_spellcheck.name

    @classmethod
    def need_product_store(cls) -> bool:
        return False

    def import_insights(self, data: Iterable[Dict], purge: bool = False):
        if purge:
            ProductInsight.delete().where(ProductInsight.type ==
                                          InsightType.
                                          ingredient_spellcheck.name).execute()
            ProductIngredient.delete().execute()

        barcode_seen: Set[str] = set()
        insight_seen: Set = set()
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


GroupedByOCRInsights = Dict[str, List]


class OCRInsightImporter(InsightImporter, metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    @classmethod
    def need_product_store(cls) -> bool:
        return True

    def import_insights(self, data: Iterable[Dict], purge: bool = False):
        grouped_by: GroupedByOCRInsights = self.group_by_barcode(data)
        inserts: List[Dict] = []

        if purge:
            ProductInsight.delete().where(ProductInsight.type ==
                                          self.get_type(),
                                          ProductInsight.annotation.is_null()
                                          ).execute()

        for barcode, insights in grouped_by.items():
            inserts += self.process_product_insights(insights)

        batch_insert(ProductInsight, inserts, 50)

    def group_by_barcode(self, data: Iterable[Dict]) -> GroupedByOCRInsights:
        grouped_by: GroupedByOCRInsights = {}
        insight_type = self.get_type()

        for item in data:
            barcode = item['barcode']
            source = item['source']

            if item['type'] != insight_type:
                raise ValueError("unexpected insight type: "
                                 "'{}'".format(insight_type))

            insights = item['insights']

            if not insights:
                continue

            grouped_by.setdefault(barcode, [])
            grouped_by[barcode] += [{
                'source': source,
                'barcode': barcode,
                'type': insight_type,
                'content': i,
            } for i in insights]

        return grouped_by

    @abc.abstractmethod
    def process_product_insights(self, insights: List[JSONType]) \
            -> List[JSONType]:
        pass


class PackagerCodeInsightImporter(OCRInsightImporter):
    def get_type(self) -> str:
        return InsightType.packager_code.name

    def process_product_insights(self, insights: List[JSONType]) \
            -> List[JSONType]:
        processed: List[JSONType] = []

        code_seen = set(t.text for t in
                        ProductInsight.select(ProductInsight.data['text']
                                              .as_json().alias('text'))
                                      .where(
                            ProductInsight.annotation.is_null(False),
                            ProductInsight.type ==
                            self.get_type()))

        for insight in insights:
            barcode = insight['barcode']
            content = insight['content']
            emb_code = content['text']

            if self.product_store:
                product = self.product_store[barcode]

                if not product:
                    continue

                emb_code_tag = self.get_emb_code_tag(emb_code)

                if (emb_code_tag in product.emb_codes_tags or
                        (emb_code_tag.endswith('ce') and
                         emb_code_tag.replace('ce', 'ec')
                         in product.emb_codes_tags)):
                    continue

            if emb_code in code_seen:
                continue

            processed.append({
                'id': str(uuid.uuid4()),
                'type': self.get_type(),
                'barcode': barcode,
                'countries': product.countries_tags,
                'data': {
                    'source': insight['source'],
                    'matcher_type': content['type'],
                    'raw': content['raw'],
                    'text': emb_code,
                }
            })
            code_seen.add(emb_code)

        return processed

    @staticmethod
    def get_emb_code_tag(emb_code: str) -> str:
        return (emb_code.lower()
                .replace(' ', '-')
                .replace('.', '-'))


class LabelInsightImporter(OCRInsightImporter):
    def get_type(self) -> str:
        return InsightType.label.name

    def process_product_insights(self, insights: List[JSONType]) \
            -> List[JSONType]:
        processed: List[JSONType] = []
        label_seen: Set[str] = set()

        for insight in insights:
            barcode = insight['barcode']
            content = insight['content']
            label_tag = content['label_tag']

            if self.product_store:
                product = self.product_store[barcode]

                if not product:
                    continue

                if label_tag in product.labels_tags:
                    continue

            if label_tag in label_seen:
                continue

            processed.append({
                'id': str(uuid.uuid4()),
                'type': self.get_type(),
                'barcode': barcode,
                'countries': product.countries_tags,
                'data': {
                    'source': insight['source'],
                    'text': content['text'],
                    'label_tag': label_tag,
                }
            })
            label_seen.add(label_tag)

        return processed

    def need_validation(self, insight: ProductInsight) -> bool:
        if insight.type != self.get_type():
            raise ValueError("insight must be of type {}".format(self.get_type()))

        if insight.data['label_tag'] in AUTHORIZED_LABELS:
            return False

        return True


class CategoryImporter(InsightImporter):
    def get_type(self) -> str:
        return InsightType.category.name

    def need_product_store(self) -> bool:
        return True

    def import_insights(self, data: Iterable[Dict], purge: bool = False):
        if purge:
            ProductInsight.delete().where(ProductInsight.type ==
                                          self.get_type(),
                                          ProductInsight.annotation.is_null()
                                          ).execute()

        exclude_set: Set[str] = set(
            ProductInsight.select(ProductInsight.barcode)
                          .scalar())

        inserts = (self.process_product_insight(insight)
                   for insight in data
                   if insight is not None and insight not in exclude_set)
        batch_insert(ProductInsight, inserts)

    def process_product_insight(self, insight: JSONType) \
            -> Optional[JSONType]:
        insert = {
            'id': str(uuid.uuid4()),
            'barcode': insight['barcode'],
            'data': {
                'category': insight['category'],
                'confidence': insight.get('predicted_category_prob'),
            }
        }

        if 'category_depth' in insight:
            insert['category_depth'] = insight['category_depth']

        if 'model' is not None:
            insert['model'] = insight['model']

        yield insert


class InsightImporterFactory:
    importers: JSONType = {
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckImporter,
        InsightType.packager_code.name: PackagerCodeInsightImporter,
        InsightType.label.name: LabelInsightImporter,
        InsightType.category.name: CategoryImporter,
    }

    @classmethod
    def create(cls, insight_type: str):
        if insight_type in cls.importers:
            return cls.importers[insight_type]
        else:
            raise ValueError("unknown insight type: {}".format(insight_type))
