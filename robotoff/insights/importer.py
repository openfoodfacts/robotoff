import abc
import uuid
from typing import Dict, Iterable, List, Set, Optional

from robotoff.insights._enum import InsightType
from robotoff.insights.data import AUTHORIZED_LABELS
from robotoff.models import batch_insert, ProductInsight, ProductIngredient
from robotoff.products import ProductStore, Product
from robotoff.taxonomy import TAXONOMY_STORES, Taxonomy, TaxonomyNode
from robotoff.utils import get_logger, jsonl_iter, jsonl_iter_fp
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


class InsightImporter(metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    @abc.abstractmethod
    def import_insights(self, data: Iterable[Dict], purge: bool = False) -> int:
        pass

    @abc.abstractmethod
    def get_type(self) -> str:
        pass

    def from_jsonl(self, file_path):
        items = jsonl_iter(file_path)
        self.import_insights(items)

    def from_jsonl_fp(self, fp):
        items = jsonl_iter_fp(fp)
        self.import_insights(items)

    def need_validation(self, insight: ProductInsight) -> bool:
        return True
    
    def purge_insights(self):
        ProductInsight.delete().where(ProductInsight.type ==
                                      self.get_type(),
                                      ProductInsight.annotation.is_null()
                                      ).execute()


class IngredientSpellcheckImporter(InsightImporter):
    def get_type(self) -> str:
        return InsightType.ingredient_spellcheck.name

    def purge_insights(self):
        # Purge all non-annotated insights, partial updates are not allowed
        ProductInsight.delete().where(ProductInsight.type ==
                                      self.get_type(),
                                      ProductInsight.annotation.is_null()
                                      ).execute()
        ProductIngredient.delete().execute()
    
    def import_insights(self, data: Iterable[Dict], purge: bool = True) -> int:
        if purge:
            self.purge_insights()

        barcode_seen: Set[str] = set()
        insight_seen: Set = set()
        insights = []
        product_ingredients = []
        inserted = 0

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
                inserted += batch_insert(ProductInsight, insights, 50)
                insights = []

        batch_insert(ProductIngredient, product_ingredients, 50)
        inserted += batch_insert(ProductInsight, insights, 50)
        return inserted

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
    def import_insights(self, data: Iterable[Dict], purge: bool = False) -> int:
        grouped_by: GroupedByOCRInsights = self.group_by_barcode(data)
        inserts: List[Dict] = []

        if purge:
            self.purge_insights()

        for barcode, insights in grouped_by.items():
            inserts += list(self.process_product_insights(insights))

        return batch_insert(ProductInsight, inserts, 50)

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
    def process_product_insights(self, insights: Iterable[JSONType]) \
            -> Iterable[JSONType]:
        pass


class PackagerCodeInsightImporter(OCRInsightImporter):
    def get_type(self) -> str:
        return InsightType.packager_code.name

    def is_valid(self, barcode: str,
                 emb_code: str,
                 code_seen: Dict[str, Set[str]]) -> bool:
        product: Optional[Product] = self.product_store[barcode]

        if not product:
            # Product is not yet part of the dump, or has been deleted
            # since insights generation. By default, include it.
            return True

        emb_code_tag = self.get_emb_code_tag(emb_code)

        if (emb_code_tag in product.emb_codes_tags or
                (emb_code_tag.endswith('ce') and
                 emb_code_tag.replace('ce', 'ec')
                 in product.emb_codes_tags)):
            return False

        if emb_code in code_seen.get(barcode, set()):
            return False
        
        return True
    
    def process_product_insights(self, insights: Iterable[JSONType]) \
            -> Iterable[JSONType]:
        code_seen: Dict[str, Set[str]] = {}
        for t in (ProductInsight.select(ProductInsight.data['text']
                                        .as_json().alias('text'),
                                        ProductInsight.barcode)
                                .where(ProductInsight.type ==
                                       self.get_type())).iterator():
            code_seen.setdefault(t.barcode, set())
            code_seen[t.barcode].add(t.text)

        for insight in insights:
            barcode = insight['barcode']
            content = insight['content']
            emb_code = content['text']
            
            if not self.is_valid(barcode, emb_code, code_seen):
                continue

            countries_tags = getattr(self.product_store[barcode],
                                     'countries_tags', [])
            yield {
                'id': str(uuid.uuid4()),
                'type': self.get_type(),
                'barcode': barcode,
                'countries': countries_tags,
                'data': {
                    'source': insight['source'],
                    'matcher_type': content['type'],
                    'raw': content['raw'],
                    'text': emb_code,
                }
            }
            code_seen.setdefault(barcode, set())
            code_seen[barcode].add(emb_code)

    @staticmethod
    def get_emb_code_tag(emb_code: str) -> str:
        return (emb_code.lower()
                .replace(' ', '-')
                .replace('.', '-'))


class LabelInsightImporter(OCRInsightImporter):
    def get_type(self) -> str:
        return InsightType.label.name

    def is_valid(self, barcode: str,
                 label_tag: str,
                 label_seen: Dict[str, Set[str]]) -> bool:
        product = self.product_store[barcode]

        if not product:
            return True

        if label_tag in product.labels_tags:
            return False

        if label_tag in label_seen.get(barcode, set()):
            return False
        
        return True
    
    def process_product_insights(self, insights: Iterable[JSONType]) \
            -> Iterable[JSONType]:
        label_seen: Dict[str, Set[str]] = {}
        for t in (ProductInsight.select(ProductInsight.data['label_tag']
                                        .as_json().alias('label_tag'),
                                        ProductInsight.barcode)
                                .where(ProductInsight.type ==
                                       self.get_type())).iterator():
            label_seen.setdefault(t.barcode, set())
            label_seen[t.barcode].add(t.label_tag)

        for insight in insights:
            barcode = insight['barcode']
            content = insight['content']
            label_tag = content['label_tag']

            if not self.is_valid(barcode, label_tag, label_seen):
                continue

            countries_tags = getattr(self.product_store[barcode],
                                     'countries_tags', [])
            yield {
                'id': str(uuid.uuid4()),
                'type': self.get_type(),
                'barcode': barcode,
                'countries': countries_tags,
                'data': {
                    'source': insight['source'],
                    'text': content['text'],
                    'label_tag': label_tag,
                }
            }
            label_seen.setdefault(barcode, set())
            label_seen[barcode].add(label_tag)

    def need_validation(self, insight: ProductInsight) -> bool:
        if insight.type != self.get_type():
            raise ValueError("insight must be of type "
                             "{}".format(self.get_type()))

        if insight.data['label_tag'] in AUTHORIZED_LABELS:
            return False

        return True


class CategoryImporter(InsightImporter):
    def get_type(self) -> str:
        return InsightType.category.name

    def import_insights(self, data: Iterable[Dict], purge: bool = False) -> int:
        if purge:
            self.purge_insights()

        inserts = self.process_product_insights(data)
        return batch_insert(ProductInsight, inserts, 50)

    def process_product_insights(self, insights: Iterable[JSONType]) \
            -> Iterable[JSONType]:
        category_seen: Dict[str, Set[str]] = {}
        for t in (ProductInsight.select(ProductInsight.data['category']
                                        .as_json().alias('category'),
                                        ProductInsight.barcode)
                                .where(ProductInsight.type ==
                                       self.get_type())).iterator():
            category_seen.setdefault(t.barcode, set())
            category_seen[t.barcode].add(t.category)

        for insight in insights:
            barcode = insight['barcode']
            category = insight['category']

            if not self.is_valid(barcode, category, category_seen):
                continue

            countries_tags = getattr(self.product_store[barcode],
                                     'countries_tags', [])
            insert = {
                'id': str(uuid.uuid4()),
                'type': self.get_type(),
                'barcode': barcode,
                'countries': countries_tags,
                'data': {
                    'category': category,
                }
            }

            if 'category_depth' in insight:
                insert['data']['category_depth'] = insight['category_depth']

            if 'model' in insight:
                insert['data']['model'] = insight['model']

            if 'confidence' in insight:
                insert['data']['confidence'] = insight['confidence']

            yield insert
            category_seen.setdefault(barcode, set())
            category_seen[barcode].add(category)

    def is_valid(self, barcode: str,
                 category: str,
                 category_seen: Dict[str, Set[str]]):
        product = self.product_store[barcode]

        if not product:
            logger.debug("Product is not in product store, considering "
                         "the insight as valid")
            return True

        if category in product.categories_tags:
            logger.debug("The product already belongs to this category, "
                         "considering the insight as invalid")
            return False

        if category in category_seen.get(barcode, set()):
            logger.debug("An insight already exists for this product and "
                         "category, considering the insight as invalid")
            return False

        # Check that the predicted category is not a parent of a
        # current/already predicted category
        category_taxonomy: Taxonomy = TAXONOMY_STORES[
            InsightType.category.name].get()

        if category in category_taxonomy:
            category_node: TaxonomyNode = category_taxonomy[category]

            to_check_categories = (set(product.categories_tags)
                                   .union(category_seen.get(barcode,
                                                            set())))
            for other_category_node in (category_taxonomy[to_check_category]
                                        for to_check_category
                                        in to_check_categories):
                if (other_category_node is not None and
                        other_category_node.is_child_of(category_node)):
                    logger.debug(
                        "The predicted category is a child of the product "
                        "category or of the predicted category of an insight, "
                        "considering the insight as invalid")
                    return False

        return True


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
