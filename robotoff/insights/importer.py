import abc
import datetime
import operator
import uuid
from typing import Dict, Iterable, List, Set, Optional, Callable

from robotoff.insights._enum import InsightType
from robotoff.insights.data import AUTHORIZED_LABELS, BRANDS_BARCODE_RANGE
from robotoff.insights.normalize import normalize_emb_code
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

    @staticmethod
    @abc.abstractmethod
    def get_type() -> str:
        pass

    def from_jsonl(self, file_path):
        items = jsonl_iter(file_path)
        self.import_insights(items)

    def from_jsonl_fp(self, fp):
        items = jsonl_iter_fp(fp)
        self.import_insights(items)

    @staticmethod
    def need_validation(insight: ProductInsight) -> bool:
        return True
    
    def purge_insights(self):
        ProductInsight.delete().where(ProductInsight.type ==
                                      self.get_type(),
                                      ProductInsight.annotation.is_null()
                                      ).execute()

    @staticmethod
    def _deduplicate_insights(data: Iterable[Dict],
                              key_func: Callable) -> Iterable[Dict]:
        seen: Set = set()
        for item in data:
            value = key_func(item)
            if value in seen:
                continue

            seen.add(value)
            yield item


class IngredientSpellcheckImporter(InsightImporter):
    @staticmethod
    def get_type() -> str:
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

        timestamp = datetime.datetime.utcnow()
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
                        'timestamp': timestamp,
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

        timestamp = datetime.datetime.utcnow()

        for barcode, insights in grouped_by.items():
            insights = list(self.deduplicate_insights(insights))
            insights = self.sort_by_priority(insights)
            inserts += list(self._process_product_insights(barcode, insights,
                                                           timestamp))

        return batch_insert(ProductInsight, inserts, 50)

    def _process_product_insights(self, barcode: str,
                                  insights: List[JSONType],
                                  timestamp: datetime.datetime) -> \
            Iterable[JSONType]:
        countries_tags = getattr(self.product_store[barcode],
                                 'countries_tags', [])
        brands_tags = getattr(self.product_store[barcode],
                              'brands_tags', [])

        for insight in self.process_product_insights(barcode, insights):
            insight['id'] = str(uuid.uuid4())
            insight['barcode'] = barcode
            insight['timestamp'] = timestamp
            insight['type'] = self.get_type()
            insight['countries'] = countries_tags
            insight['brands'] = brands_tags
            yield insight

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

    @staticmethod
    def sort_by_priority(insights: List[JSONType]) -> List[JSONType]:
        return sorted(insights,
                      key=lambda insight: insight.get('priority', 1))

    @abc.abstractmethod
    def process_product_insights(self, barcode: str,
                                 insights: List[JSONType]) \
            -> Iterable[JSONType]:
        pass

    @abc.abstractmethod
    def deduplicate_insights(self, data: Iterable[JSONType]) -> \
            Iterable[JSONType]:
        pass


class PackagerCodeInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self,
                             data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(data,
                                              lambda x: x['content']['text'])

    @staticmethod
    def get_type() -> str:
        return InsightType.packager_code.name

    def is_valid(self, barcode: str,
                 emb_code: str,
                 code_seen: Set[str]) -> bool:
        product: Optional[Product] = self.product_store[barcode]

        if not product:
            # Product is not yet part of the dump, or has been deleted
            # since insights generation. By default, include it.
            return True

        normalized_emb_code = normalize_emb_code(emb_code)
        normalized_emb_codes = [normalize_emb_code(c)
                                for c in product.emb_codes_tags]

        if normalized_emb_code in normalized_emb_codes:
            return False

        if emb_code in code_seen:
            return False
        
        return True
    
    def process_product_insights(self, barcode: str,
                                 insights: List[JSONType]) \
            -> Iterable[JSONType]:
        code_seen: Set[str] = set()

        for t in (ProductInsight.select(ProductInsight.data['text']
                                        .as_json().alias('text'))
                                .where(ProductInsight.type ==
                                       self.get_type(),
                                       ProductInsight.barcode ==
                                       barcode)).iterator():
            code_seen.add(t.text)

        for insight in insights:
            content = insight['content']
            emb_code = content['text']
            
            if not self.is_valid(barcode, emb_code, code_seen):
                continue

            source = insight['source']
            yield {
                'source_image': source,
                'data': {
                    'source': source,
                    'matcher_type': content['type'],
                    'raw': content['raw'],
                    'text': emb_code,
                    'notify': content['notify'],
                }
            }
            code_seen.add(emb_code)

    @staticmethod
    def need_validation(insight: ProductInsight) -> bool:
        if insight.type != PackagerCodeInsightImporter.get_type():
            raise ValueError("insight must be of type "
                             "{}".format(PackagerCodeInsightImporter
                                         .get_type()))

        if insight.data['matcher_type'] in ('eu_fr', 'eu_de', 'fr_emb'):
            return False

        return True


class LabelInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self,
                             data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(
            data, lambda x: x['content']['label_tag'])

    @staticmethod
    def get_type() -> str:
        return InsightType.label.name

    def is_valid(self, barcode: str,
                 label_tag: str,
                 label_seen: Set[str]) -> bool:
        product = self.product_store[barcode]

        if not product:
            return True

        if label_tag in product.labels_tags:
            return False

        if label_tag in label_seen:
            return False

        # Check that the predicted label is not a parent of a
        # current/already predicted label
        label_taxonomy: Taxonomy = TAXONOMY_STORES[
            InsightType.label.name].get()

        if label_tag in label_taxonomy:
            label_node: TaxonomyNode = label_taxonomy[label_tag]

            to_check_labels = (set(product.labels_tags)
                               .union(label_seen))
            for other_label_node in (label_taxonomy[to_check_label]
                                     for to_check_label
                                     in to_check_labels):
                if (other_label_node is not None and
                        other_label_node.is_child_of(label_node)):
                    return False
        
        return True
    
    def process_product_insights(self, barcode: str,
                                 insights: List[JSONType]) \
            -> Iterable[JSONType]:
        label_seen: Set[str] = set()

        for t in (ProductInsight.select(ProductInsight.value_tag)
                                .where(ProductInsight.type ==
                                       self.get_type(),
                                       ProductInsight.barcode ==
                                       barcode)).iterator():
            label_seen.add(t.value_tag)

        for insight in insights:
            barcode = insight['barcode']
            content = insight['content']
            label_tag = content['label_tag']

            if not self.is_valid(barcode, label_tag, label_seen):
                continue

            source = insight['source']
            yield {
                'value_tag': label_tag,
                'source_image': source,
                'data': {
                    'source': source,
                    'text': content['text'],
                    'label_tag': label_tag,
                    'notify': content['notify'],
                }
            }
            label_seen.add(label_tag)

    @staticmethod
    def need_validation(insight: ProductInsight) -> bool:
        if insight.type != LabelInsightImporter.get_type():
            raise ValueError("insight must be of type "
                             "{}".format(LabelInsightImporter.get_type()))

        if insight.data['label_tag'] in AUTHORIZED_LABELS:
            return False

        return True


class CategoryImporter(InsightImporter):
    def deduplicate_insights(self,
                             data: Iterable[JSONType]) -> Iterable[JSONType]:
        key_func = operator.itemgetter('category')
        yield from self._deduplicate_insights(data, key_func)

    @staticmethod
    def get_type() -> str:
        return InsightType.category.name

    def import_insights(self, data: Iterable[Dict], purge: bool = False) -> int:
        if purge:
            self.purge_insights()

        data = self.deduplicate_insights(data)
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

        timestamp = datetime.datetime.utcnow()
        for insight in insights:
            barcode = insight['barcode']
            category = insight['category']

            if not self.is_valid(barcode, category, category_seen):
                continue

            countries_tags = getattr(self.product_store[barcode],
                                     'countries_tags', [])
            brands_tags = getattr(self.product_store[barcode],
                                  'brands_tags', [])

            insert = {
                'id': str(uuid.uuid4()),
                'type': self.get_type(),
                'barcode': barcode,
                'countries': countries_tags,
                'brands': brands_tags,
                'timestamp': timestamp,
                'value_tag': category,
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
                        "The predicted category is a parent of the product "
                        "category or of the predicted category of an insight, "
                        "considering the insight as invalid")
                    return False

        return True


class ProductWeightImporter(OCRInsightImporter):
    def deduplicate_insights(self,
                             data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(
            data, lambda x: x['content']['text'])

    @staticmethod
    def get_type() -> str:
        return InsightType.product_weight.name

    def is_valid(self, barcode: str, weight_value_str: str) -> bool:
        product = self.product_store[barcode]

        if not product:
            return True

        if product.quantity is not None:
            logger.debug("Product quantity field is not null, returning "
                         "non valid")
            return False

        try:
            weight_value = float(weight_value_str)
        except ValueError:
            logger.warn("Weight value is not a float: {}"
                        "".format(weight_value_str))
            return False

        if weight_value <= 0:
            logger.debug("Weight value is <= 0")
            return False

        return True

    @staticmethod
    def group_by_subtype(insights: List[JSONType]) -> Dict[str, List[JSONType]]:
        insights_by_subtype: Dict[str, List[JSONType]] = {}

        for insight in insights:
            matcher_type = insight['content']['matcher_type']
            insights_by_subtype.setdefault(matcher_type, [])
            insights_by_subtype[matcher_type].append(insight)

        return insights_by_subtype

    def process_product_insights(self, barcode: str,
                                 insights: List[JSONType]) \
            -> Iterable[JSONType]:
        if not insights:
            return

        insights_by_subtype = self.group_by_subtype(insights)

        insight = insights[0]
        insight_subtype = insight['content']['matcher_type']

        if (insight_subtype != 'with_mention' and
                len(insights_by_subtype[insight_subtype]) > 1):
            logger.info("{} distinct product weights found for product "
                        "{}, aborting import".format(len(insights),
                                                     barcode))
            return

        if ProductInsight.select().where(ProductInsight.type ==
                                         self.get_type(),
                                         ProductInsight.barcode ==
                                         barcode).count():
            return

        content = insight['content']

        if not self.is_valid(barcode, content['value']):
            return

        source = insight['source']
        yield {
            'source_image': source,
            'data': {
                'source': source,
                'notify': content['notify'],
                **content
            }
        }

    @staticmethod
    def need_validation(insight: ProductInsight) -> bool:
        return False


class ExpirationDateImporter(OCRInsightImporter):
    def deduplicate_insights(self,
                             data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(
            data, lambda x: x['content']['text'])

    @staticmethod
    def get_type() -> str:
        return InsightType.expiration_date.name

    def is_valid(self, barcode: str) -> bool:
        product = self.product_store[barcode]

        if not product:
            return True

        if product.expiration_date:
            logger.debug("Product expiration date field is not null, returning "
                         "non valid")
            return False

        return True

    def process_product_insights(self, barcode: str,
                                 insights: List[JSONType]) \
            -> Iterable[JSONType]:
        if len(insights) > 1:
            logger.info("{} distinct expiration dates found for product "
                        "{}, aborting import".format(len(insights),
                                                     barcode))
            return

        if ProductInsight.select().where(ProductInsight.type ==
                                         self.get_type(),
                                         ProductInsight.barcode ==
                                         barcode).count():
            return

        for insight in insights:
            content = insight['content']

            if not self.is_valid(barcode):
                continue

            source = insight['source']
            yield {
                'source_image': source,
                'data': {
                    'source': source,
                    'notify': content['notify'],
                    **content
                }
            }
            break

    @staticmethod
    def need_validation(insight: ProductInsight) -> bool:
        return False


class BrandInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self,
                             data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(
            data, lambda x: x['content']['brand_tag'])

    @staticmethod
    def get_type() -> str:
        return InsightType.brand.name

    def is_valid(self, barcode: str,
                 brand_tag: str,
                 brand_seen: Set[str]) -> bool:
        product = self.product_store[barcode]

        if not product:
            return True

        if product.brands_tags:
            # For now, don't annotate if a brand has already been provided
            return False

        if brand_tag in brand_seen:
            return False

        if not self.in_barcode_range(brand_tag, barcode):
            logger.warn("Barcode {} of brand {} not in barcode "
                        "range".format(barcode, brand_tag))
            return False

        return True

    def process_product_insights(self, barcode: str,
                                 insights: List[JSONType]) \
            -> Iterable[JSONType]:
        brand_seen: Set[str] = set()

        for t in (ProductInsight.select(ProductInsight.value_tag)
                .where(ProductInsight.type ==
                       self.get_type(),
                       ProductInsight.barcode ==
                       barcode)).iterator():
            brand_seen.add(t.value_tag)

        for insight in insights:
            barcode = insight['barcode']
            content = insight['content']
            brand_tag = content['brand_tag']

            if not self.is_valid(barcode, brand_tag, brand_seen):
                continue

            source = insight['source']
            yield {
                'value_tag': brand_tag,
                'source_image': source,
                'data': {
                    'source': source,
                    'brand_tag': brand_tag,
                    'text': content['text'],
                    'brand': content['brand'],
                    'notify': content['notify'],
                }
            }
            brand_seen.add(brand_tag)

    @staticmethod
    def need_validation(insight: ProductInsight) -> bool:
        return False

    @staticmethod
    def in_barcode_range(brand_tag: str, barcode: str) -> bool:
        """Check that the insight barcode is in the range of the detected
        brand barcode range.
        Return True if the check passes, False otherwise
        """
        if brand_tag not in BRANDS_BARCODE_RANGE:
            return True

        barcode_range = BRANDS_BARCODE_RANGE[brand_tag]

        if len(barcode_range) != len(barcode):
            logger.debug("Barcode range and barcode do not have the same length")
            return True

        barcode_range = barcode_range.replace('x', '')

        if barcode.startswith(barcode_range):
            return True

        logger.debug("Barcode {} not in range {}".format(barcode, barcode_range))
        return False


class InsightImporterFactory:
    importers: JSONType = {
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckImporter,
        InsightType.packager_code.name: PackagerCodeInsightImporter,
        InsightType.label.name: LabelInsightImporter,
        InsightType.category.name: CategoryImporter,
        InsightType.product_weight.name: ProductWeightImporter,
        InsightType.expiration_date.name: ExpirationDateImporter,
        InsightType.brand.name: BrandInsightImporter,
    }

    @classmethod
    def create(cls, insight_type: str,
               product_store: Optional[ProductStore]) -> InsightImporter:
        if insight_type in cls.importers:
            return cls.importers[insight_type](product_store)
        else:
            raise ValueError("unknown insight type: {}".format(insight_type))
