import abc
import datetime
import pathlib
import uuid
from typing import Dict, Iterable, List, Set, Optional, Callable, Tuple

from robotoff.brands import BRAND_PREFIX_STORE, in_barcode_range, BRAND_BLACKLIST_STORE
from robotoff.insights._enum import InsightType
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import batch_insert, ProductInsight
from robotoff.off import get_server_type
from robotoff.products import ProductStore, Product
from robotoff import settings
from robotoff.taxonomy import Taxonomy, TaxonomyNode, get_taxonomy
from robotoff.utils import get_logger, jsonl_iter, jsonl_iter_fp, text_file_iter
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def load_authorized_labels() -> Set[str]:
    return set(text_file_iter(settings.OCR_LABEL_WHITELIST_DATA_PATH))


AUTHORIZED_LABELS_STORE = CachedStore(load_authorized_labels, expiration_interval=None)


def generate_seen_set_query(insight_type: str, barcode: str, server_domain: str):
    return ProductInsight.select(ProductInsight.value_tag).where(
        ProductInsight.type == insight_type,
        ProductInsight.barcode == barcode,
        ProductInsight.server_domain == server_domain,
    )


def is_reserved_barcode(barcode: str) -> bool:
    if barcode.startswith("0"):
        barcode = barcode[1:]

    return barcode.startswith("2")


class InsightImporter(metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    def import_insights(
        self, data: Iterable[JSONType], server_domain: str, automatic: bool
    ) -> int:
        timestamp = datetime.datetime.utcnow()
        insights = self.process_insights(data, server_domain, automatic)
        insights = self.add_fields(insights, timestamp, server_domain)
        return batch_insert(ProductInsight, insights, 50)

    @abc.abstractmethod
    def process_insights(
        self, data: Iterable[JSONType], server_domain: str, automatic: bool
    ) -> Iterable[JSONType]:
        pass

    def add_fields(
        self,
        insights: Iterable[JSONType],
        timestamp: datetime.datetime,
        server_domain: str,
    ) -> Iterable[JSONType]:
        """Add mandatory insight fields."""
        server_type: str = get_server_type(server_domain).name

        for insight in insights:
            barcode = insight["barcode"]
            product = self.product_store[barcode]
            insight["reserved_barcode"] = is_reserved_barcode(barcode)
            insight["server_domain"] = server_domain
            insight["server_type"] = server_type
            insight["id"] = str(uuid.uuid4())
            insight["timestamp"] = timestamp
            insight["type"] = self.get_type()
            insight["countries"] = getattr(product, "countries_tags", [])
            insight["brands"] = getattr(product, "brands_tags", [])
            yield insight

    @staticmethod
    @abc.abstractmethod
    def get_type() -> str:
        pass

    def from_jsonl(self, file_path: pathlib.Path, server_domain: str):
        items = jsonl_iter(file_path)
        self.import_insights(items, server_domain=server_domain, automatic=False)

    def from_jsonl_fp(self, fp, server_domain: str):
        items = jsonl_iter_fp(fp)
        self.import_insights(items, server_domain=server_domain, automatic=False)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return True

    @staticmethod
    def _deduplicate_insights(
        data: Iterable[Dict], key_func: Callable
    ) -> Iterable[Dict]:
        seen: Set = set()
        for item in data:
            value = key_func(item)
            if value in seen:
                continue

            seen.add(value)
            yield item

    @classmethod
    def get_seen_set(cls, barcode: str, server_domain: str) -> Set[str]:
        seen_set: Set[str] = set()
        query = generate_seen_set_query(cls.get_type(), barcode, server_domain)

        for t in query.iterator():
            seen_set.add(t.value_tag)

        return seen_set

    @classmethod
    def get_seen_count(cls, barcode: str, server_domain: str) -> int:
        query = generate_seen_set_query(cls.get_type(), barcode, server_domain)
        return query.count()


GroupedByOCRInsights = Dict[str, List]


class OCRInsightImporter(InsightImporter, metaclass=abc.ABCMeta):
    def process_insights(
        self, data: Iterable[JSONType], server_domain: str, automatic: bool
    ) -> Iterable[JSONType]:
        grouped_by: GroupedByOCRInsights = self.group_by_barcode(data)
        inserts: List[JSONType] = []

        for barcode, insights in grouped_by.items():
            insights = list(self.deduplicate_insights(insights))
            insights = self.sort_by_priority(insights)
            inserts += list(
                self._process_product_insights(
                    barcode, insights, automatic, server_domain
                )
            )

        return inserts

    def _process_product_insights(
        self,
        barcode: str,
        insights: List[JSONType],
        automatic: bool,
        server_domain: str,
    ) -> Iterable[JSONType]:
        for insight in self.process_product_insights(barcode, insights, server_domain):
            insight["barcode"] = barcode

            if not automatic:
                insight["automatic_processing"] = False

            elif "automatic_processing" not in insights:
                insight["automatic_processing"] = not self.need_validation(insight)

            yield insight

    def group_by_barcode(self, data: Iterable[Dict]) -> GroupedByOCRInsights:
        grouped_by: GroupedByOCRInsights = {}
        insight_type = self.get_type()

        for item in data:
            barcode = item["barcode"]
            source = item.get("source")

            if item["type"] != insight_type:
                raise ValueError(
                    "unexpected insight type: " "'{}'".format(insight_type)
                )

            insights = item["insights"]

            if not insights:
                continue

            grouped_by.setdefault(barcode, [])
            grouped_by[barcode] += [
                {
                    "source": source,
                    "barcode": barcode,
                    "type": insight_type,
                    "content": i,
                }
                for i in insights
            ]

        return grouped_by

    @staticmethod
    def sort_by_priority(insights: List[JSONType]) -> List[JSONType]:
        return sorted(insights, key=lambda insight: insight.get("priority", 1))

    @abc.abstractmethod
    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        pass

    @abc.abstractmethod
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        pass


class PackagerCodeInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(data, lambda x: x["content"]["text"])

    @staticmethod
    def get_type() -> str:
        return InsightType.packager_code.name

    def is_valid(self, barcode: str, emb_code: str, code_seen: Set[str]) -> bool:
        product: Optional[Product] = self.product_store[barcode]
        product_emb_codes_tags = getattr(product, "emb_codes_tags", [])

        normalized_emb_code = normalize_emb_code(emb_code)
        normalized_emb_codes = [normalize_emb_code(c) for c in product_emb_codes_tags]

        if normalized_emb_code in normalized_emb_codes:
            return False

        if emb_code in code_seen:
            return False

        return True

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        seen_set: Set[str] = set()

        for t in (
            ProductInsight.select(ProductInsight.value).where(
                ProductInsight.type == self.get_type(),
                ProductInsight.barcode == barcode,
                ProductInsight.server_domain == server_domain,
            )
        ).iterator():
            seen_set.add(t.value)

        for insight in insights:
            content = insight["content"]
            emb_code = content["text"]

            if not self.is_valid(barcode, emb_code, seen_set):
                continue

            yield {
                "source_image": insight["source"],
                "value": emb_code,
                "data": {
                    "matcher_type": content["type"],
                    "raw": content["raw"],
                    "notify": content["notify"],
                },
            }
            seen_set.add(emb_code)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        if insight["data"]["matcher_type"] in ("eu_fr", "eu_de", "fr_emb", "fishing"):
            return False

        return True


class LabelInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(data, lambda x: x["content"]["label_tag"])

    @staticmethod
    def get_type() -> str:
        return InsightType.label.name

    def is_valid(self, barcode: str, tag: str, seen_set: Set[str]) -> bool:
        product = self.product_store[barcode]
        product_labels_tags = getattr(product, "labels_tags", [])

        if tag in product_labels_tags:
            return False

        if tag in seen_set:
            return False

        # Check that the predicted label is not a parent of a
        # current/already predicted label
        label_taxonomy: Taxonomy = get_taxonomy(InsightType.label.name)

        if tag in label_taxonomy:
            label_node: TaxonomyNode = label_taxonomy[tag]

            to_check_labels = set(product_labels_tags).union(seen_set)
            for other_label_node in (
                label_taxonomy[to_check_label] for to_check_label in to_check_labels
            ):
                if other_label_node is not None and other_label_node.is_child_of(
                    label_node
                ):
                    return False

        return True

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content.pop("label_tag")

            if not self.is_valid(barcode, value_tag, seen_set):
                continue

            automatic_processing = content.pop("automatic_processing", None)
            insert = {
                "value_tag": value_tag,
                "source_image": insight["source"],
                "data": {**content},
            }

            if automatic_processing is not None:
                insert["automatic_processing"] = automatic_processing

            yield insert
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        authorized_labels: Set[str] = AUTHORIZED_LABELS_STORE.get()

        if insight["value_tag"] in authorized_labels:
            return False

        return True


class CategoryImporter(InsightImporter):
    @staticmethod
    def get_type() -> str:
        return InsightType.category.name

    def process_insights(
        self, data: Iterable[JSONType], server_domain: str, automatic: bool
    ) -> Iterable[JSONType]:
        category_seen: Dict[str, Set[str]] = {}
        for t in (
            ProductInsight.select(
                ProductInsight.value_tag, ProductInsight.barcode
            ).where(
                ProductInsight.type == self.get_type(),
                ProductInsight.server_domain == server_domain,
            )
        ).iterator():
            category_seen.setdefault(t.barcode, set())
            category_seen[t.barcode].add(t.value_tag)

        for insight in data:
            barcode = insight["barcode"]
            category = insight["category"]

            if not self.is_valid(barcode, category, category_seen):
                continue

            insert = {
                "barcode": barcode,
                "value_tag": category,
                "automatic_processing": False,
                "data": {},
            }

            if "category_depth" in insight:
                insert["data"]["category_depth"] = insight["category_depth"]

            if "model" in insight:
                insert["data"]["model"] = insight["model"]

            if "confidence" in insight:
                insert["data"]["confidence"] = insight["confidence"]

            if "product_name" in insight:
                insert["data"]["product_name"] = insight["product_name"]

            if "lang" in insight:
                insert["data"]["lang"] = insight["lang"]

            yield insert
            category_seen.setdefault(barcode, set())
            category_seen[barcode].add(category)

    def is_valid(self, barcode: str, category: str, category_seen: Dict[str, Set[str]]):
        product = self.product_store[barcode]
        product_categories_tags = getattr(product, "categories_tags", [])

        if category in product_categories_tags:
            logger.debug(
                "The product already belongs to this category, "
                "considering the insight as invalid"
            )
            return False

        if category in category_seen.get(barcode, set()):
            logger.debug(
                "An insight already exists for this product and "
                "category, considering the insight as invalid"
            )
            return False

        # Check that the predicted category is not a parent of a
        # current/already predicted category
        category_taxonomy: Taxonomy = get_taxonomy(InsightType.category.name)

        if category in category_taxonomy:
            category_node: TaxonomyNode = category_taxonomy[category]

            to_check_categories = set(product_categories_tags).union(
                category_seen.get(barcode, set())
            )
            for other_category_node in (
                category_taxonomy[to_check_category]
                for to_check_category in to_check_categories
            ):
                if other_category_node is not None and other_category_node.is_child_of(
                    category_node
                ):
                    logger.debug(
                        "The predicted category is a parent of the product "
                        "category or of the predicted category of an insight, "
                        "considering the insight as invalid"
                    )
                    return False

        return True


class ProductWeightImporter(OCRInsightImporter):
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(data, lambda x: x["content"]["text"])

    @staticmethod
    def get_type() -> str:
        return InsightType.product_weight.name

    def is_valid(self, barcode: str, weight_value_str: str) -> bool:
        try:
            weight_value = float(weight_value_str)
        except ValueError:
            logger.warn("Weight value is not a float: {}" "".format(weight_value_str))
            return False

        if weight_value <= 0:
            logger.debug("Weight value is <= 0")
            return False

        if float(int(weight_value)) != weight_value:
            logger.info(
                "Weight value is not an integer ({}), "
                "returning non valid".format(weight_value)
            )
            return False

        product = self.product_store[barcode]

        if not product:
            return True

        if product.quantity is not None:
            logger.debug("Product quantity field is not null, returning " "non valid")
            return False

        return True

    @staticmethod
    def group_by_subtype(insights: List[JSONType]) -> Dict[str, List[JSONType]]:
        insights_by_subtype: Dict[str, List[JSONType]] = {}

        for insight in insights:
            matcher_type = insight["content"]["matcher_type"]
            insights_by_subtype.setdefault(matcher_type, [])
            insights_by_subtype[matcher_type].append(insight)

        return insights_by_subtype

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        if not insights:
            return

        insights_by_subtype = self.group_by_subtype(insights)

        insight = insights[0]
        insight_subtype = insight["content"]["matcher_type"]

        if (
            insight_subtype != "with_mention"
            and len(insights_by_subtype[insight_subtype]) > 1
        ):
            logger.info(
                "{} distinct product weights found for product "
                "{}, aborting import".format(len(insights), barcode)
            )
            return

        if self.get_seen_count(barcode=barcode, server_domain=server_domain):
            return

        content = insight["content"]

        if not self.is_valid(barcode, content["value"]):
            return

        value = content.pop("text")
        yield {
            "source_image": insight["source"],
            "value": value,
            "data": {"notify": content["notify"], **content},
        }

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        # Validation is needed if the weight was extracted from the product name
        # (not as trustworthy as OCR)
        return insight["data"].get("source") == "product_name"


class ExpirationDateImporter(OCRInsightImporter):
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(data, lambda x: x["content"]["text"])

    @staticmethod
    def get_type() -> str:
        return InsightType.expiration_date.name

    def is_valid(self, barcode: str) -> bool:
        product = self.product_store[barcode]

        if not product:
            return True

        if product.expiration_date:
            logger.debug(
                "Product expiration date field is not null, returning " "non valid"
            )
            return False

        return True

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        if len(insights) > 1:
            logger.info(
                "{} distinct expiration dates found for product "
                "{}, aborting import".format(len(insights), barcode)
            )
            return

        if self.get_seen_count(barcode=barcode, server_domain=server_domain):
            return

        for insight in insights:
            content = insight["content"]

            if not self.is_valid(barcode):
                continue

            value = content.pop("text")
            yield {
                "source_image": insight["source"],
                "value": value,
                "data": {"notify": content["notify"], **content},
            }
            break

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return False


class BrandInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(data, lambda x: x["content"]["brand_tag"])

    @staticmethod
    def get_type() -> str:
        return InsightType.brand.name

    def is_valid(self, barcode: str, tag: str, seen_set: Set[str]) -> bool:
        brand_prefix: Set[Tuple[str, str]] = BRAND_PREFIX_STORE.get()
        brand_blacklist: Set[str] = BRAND_BLACKLIST_STORE.get()

        if tag in seen_set:
            return False

        if tag in brand_blacklist:
            return False

        if not in_barcode_range(brand_prefix, tag, barcode):
            logger.warn(
                "Barcode {} of brand {} not in barcode " "range".format(barcode, tag)
            )
            return False

        product = self.product_store[barcode]

        if not product:
            return True

        if product.brands_tags:
            # For now, don't annotate if a brand has already been provided
            return False

        return True

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content["brand_tag"]

            if not self.is_valid(barcode, value_tag, seen_set):
                continue

            insert = {
                "value_tag": value_tag,
                "value": content["brand"],
                "source_image": insight["source"],
                "data": {
                    "text": content.get("text"),
                    "data_source": content.get("data_source"),
                    "notify": content["notify"],
                },
            }

            if "source" in content:
                insert["data"]["source"] = content["source"]

            if "automatic_processing" in content:
                insert["automatic_processing"] = content["automatic_processing"]

            yield insert
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        # Validation is needed if the weight was extracted from the product name
        # (not as trustworthy as OCR)
        return insight["data"].get("source") == "product_name"


class StoreInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(data, lambda x: x["content"]["value_tag"])

    @staticmethod
    def get_type() -> str:
        return InsightType.store.name

    def is_valid(self, tag: str, seen_set: Set[str]) -> bool:
        return tag not in seen_set

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content["value_tag"]

            if not self.is_valid(value_tag, seen_set):
                continue

            insert = {
                "value_tag": value_tag,
                "value": content["value"],
                "source_image": insight["source"],
                "data": {"text": content["text"], "notify": content["notify"],},
            }

            if "automatic_processing" in content:
                insert["automatic_processing"] = content["automatic_processing"]

            yield insert
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return False


class PackagingInsightImporter(OCRInsightImporter):
    def deduplicate_insights(self, data: Iterable[JSONType]) -> Iterable[JSONType]:
        yield from self._deduplicate_insights(
            data, lambda x: x["content"]["packaging_tag"]
        )

    @staticmethod
    def get_type() -> str:
        return InsightType.packaging.name

    def is_valid(self, tag: str, seen_set: Set[str]) -> bool:
        return tag not in seen_set

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterable[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content["packaging_tag"]

            if not self.is_valid(value_tag, seen_set):
                continue

            insert = {
                "value_tag": value_tag,
                "value": content["packaging"],
                "source_image": insight["source"],
                "data": {"text": content["text"], "notify": content["notify"],},
            }

            if "automatic_processing" in content:
                insert["automatic_processing"] = content["automatic_processing"]

            yield insert
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return False


class InsightImporterFactory:
    importers: JSONType = {
        InsightType.packager_code.name: PackagerCodeInsightImporter,
        InsightType.label.name: LabelInsightImporter,
        InsightType.category.name: CategoryImporter,
        InsightType.product_weight.name: ProductWeightImporter,
        InsightType.expiration_date.name: ExpirationDateImporter,
        InsightType.brand.name: BrandInsightImporter,
        InsightType.store.name: StoreInsightImporter,
        InsightType.packaging.name: PackagingInsightImporter,
    }

    @classmethod
    def create(cls, insight_type: str, product_store: ProductStore) -> InsightImporter:
        if insight_type in cls.importers:
            return cls.importers[insight_type](product_store)
        else:
            raise ValueError("unknown insight type: {}".format(insight_type))
