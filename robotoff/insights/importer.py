import abc
import datetime
import uuid
from typing import Dict, Iterable, Iterator, List, Set, Optional, Tuple

from more_itertools import chunked

from robotoff.brands import BRAND_PREFIX_STORE, in_barcode_range, BRAND_BLACKLIST_STORE
from robotoff.insights._enum import InsightType
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import batch_insert, LatentProductInsight, ProductInsight
from robotoff.off import get_server_type
from robotoff.products import ProductStore, Product
from robotoff import settings
from robotoff.taxonomy import Taxonomy, TaxonomyNode, get_taxonomy
from robotoff.utils import get_logger, text_file_iter
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


def generate_latent_insight(insight: JSONType, valid: bool) -> JSONType:
    insight = insight.copy()
    insight.pop("automatic_processing")
    insight.pop("reserved_barcode")
    insight.pop("countries")
    insight.pop("brands")
    insight.setdefault("data", {})
    insight["data"]["valid"] = valid
    return insight


class BaseInsightImporter(metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    def import_insights(
        self,
        data: Iterable[JSONType],
        server_domain: str,
        automatic: bool,
        latent: bool = True,
    ) -> int:
        timestamp = datetime.datetime.utcnow()
        insights = self.process_insights(data, server_domain, automatic)
        insights = self.add_fields(insights, timestamp, server_domain)
        inserted = 0

        for raw_insight_batch in chunked(insights, 50):
            insight_batch = []
            latent_batch = []
            for insight in raw_insight_batch:
                # if valid field is absent, suppose all insights are valid
                # (i.e: spellcheck)
                valid = insight.pop("valid", True)

                if valid:
                    insight_batch.append(insight)
                    # if insight is valid, always add it to latent insights
                    latent_batch.append(generate_latent_insight(insight, valid))
                elif latent:
                    # invalid insight, only import is as latent if latent = True
                    latent_batch.append(generate_latent_insight(insight, valid))

            inserted += batch_insert(ProductInsight, insight_batch, 50)
            batch_insert(LatentProductInsight, latent_batch, 50)

        return inserted

    @abc.abstractmethod
    def process_insights(
        self, data: Iterable[JSONType], server_domain: str, automatic: bool
    ) -> Iterator[JSONType]:
        pass

    def add_fields(
        self,
        insights: Iterable[JSONType],
        timestamp: datetime.datetime,
        server_domain: str,
    ) -> Iterator[JSONType]:
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

    @abc.abstractmethod
    def get_type(self) -> str:
        pass

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return True

    def get_seen_set(self, barcode: str, server_domain: str) -> Set[str]:
        seen_set: Set[str] = set()
        query = generate_seen_set_query(self.get_type(), barcode, server_domain)

        for t in query.iterator():
            seen_set.add(t.value_tag)

        return seen_set

    def get_seen_count(self, barcode: str, server_domain: str) -> int:
        query = generate_seen_set_query(self.get_type(), barcode, server_domain)
        return query.count()


class IngredientSpellcheckImporter(BaseInsightImporter):
    @staticmethod
    def get_type() -> str:
        return InsightType.ingredient_spellcheck.name

    def process_insights(
        self, data: Iterable[JSONType], server_domain: str, automatic: bool = False
    ) -> Iterator[JSONType]:
        seen_set: Set[Tuple[str, str]] = set(
            (x.barcode, x.data["lang"])
            for x in ProductInsight.select(
                ProductInsight.barcode, ProductInsight.data
            ).where(
                ProductInsight.type == self.get_type(),
                ProductInsight.server_domain == server_domain,
                ProductInsight.annotation.is_null(True),
            )
        )

        for item in data:
            barcode = item.pop("barcode")
            lang = item["lang"]
            key = (barcode, lang)

            if key not in seen_set:
                seen_set.add(key)
            else:
                continue

            yield {
                "barcode": barcode,
                "automatic_processing": False,
                "data": item,
            }


GroupedByOCRInsights = Dict[str, List]


class InsightImporter(BaseInsightImporter, metaclass=abc.ABCMeta):
    def process_insights(
        self, data: Iterable[JSONType], server_domain: str, automatic: bool
    ) -> Iterator[JSONType]:
        grouped_by: GroupedByOCRInsights = self.group_by_barcode(data)

        for barcode, insights in grouped_by.items():
            insights = self.sort_by_priority(list(insights))
            yield from self._process_product_insights(
                barcode, insights, automatic, server_domain
            )

    def _process_product_insights(
        self,
        barcode: str,
        insights: List[JSONType],
        automatic: bool,
        server_domain: str,
    ) -> Iterator[JSONType]:
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
    ) -> Iterator[JSONType]:
        pass


class PackagerCodeInsightImporter(InsightImporter):
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
    ) -> Iterator[JSONType]:
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

            valid = self.is_valid(barcode, emb_code, seen_set)

            yield {
                "valid": valid,
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


class LabelInsightImporter(InsightImporter):
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
    ) -> Iterator[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content.pop("label_tag")
            valid = self.is_valid(barcode, value_tag, seen_set)

            automatic_processing = content.pop("automatic_processing", None)
            insert = {
                "valid": valid,
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

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterator[JSONType]:
        seen_set: Set[str] = self.get_seen_set(
            barcode=barcode, server_domain=server_domain
        )

        for insight in insights:
            barcode = insight["barcode"]
            content = insight["content"]
            category = content.pop("category")

            if not self.is_valid(barcode, category, seen_set):
                continue

            yield {
                "barcode": barcode,
                "value_tag": category,
                "automatic_processing": False,
                "data": content,
            }
            seen_set.add(category)

    def is_valid(self, barcode: str, category: str, seen_set: Set[str]):
        product = self.product_store[barcode]
        product_categories_tags = getattr(product, "categories_tags", [])

        if category in product_categories_tags:
            logger.debug(
                "The product already belongs to this category, "
                "considering the insight as invalid"
            )
            return False

        if category in seen_set:
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

            to_check_categories = set(product_categories_tags).union(seen_set)
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


class ProductWeightImporter(InsightImporter):
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
            logger.debug("Product quantity field is not null, returning non valid")
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
    ) -> Iterator[JSONType]:
        if not insights:
            return

        insights_by_subtype = self.group_by_subtype(insights)

        insight = insights[0]
        insight_subtype = insight["content"]["matcher_type"]

        all_invalid = False
        if (
            insight_subtype != "with_mention"
            and len(insights_by_subtype[insight_subtype]) > 1
        ):
            logger.info(
                "{} distinct product weights found for product "
                "{}, aborting import".format(len(insights), barcode)
            )
            all_invalid = True

        if self.get_seen_count(barcode=barcode, server_domain=server_domain):
            all_invalid = True

        content = insight["content"]

        valid = self.is_valid(barcode, content["value"]) and not all_invalid
        value = content.pop("text")
        yield {
            "valid": valid,
            "source_image": insight["source"],
            "value": value,
            "data": {"notify": content["notify"], **content},
        }

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        # Validation is needed if the weight was extracted from the product name
        # (not as trustworthy as OCR)
        return insight["data"].get("source") == "product_name"


class ExpirationDateImporter(InsightImporter):
    @staticmethod
    def get_type() -> str:
        return InsightType.expiration_date.name

    def is_valid(self, barcode: str) -> bool:
        product = self.product_store[barcode]

        if not product:
            return True

        if product.expiration_date:
            logger.debug(
                "Product expiration date field is not null, returning non valid"
            )
            return False

        return True

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterator[JSONType]:
        all_invalid = False
        if len(insights) > 1:
            logger.info(
                "{} distinct expiration dates found for product "
                "{}, aborting import".format(len(insights), barcode)
            )
            all_invalid = True

        if self.get_seen_count(barcode=barcode, server_domain=server_domain):
            all_invalid = True

        for insight in insights:
            content = insight["content"]

            valid = self.is_valid(barcode) and not all_invalid
            value = content.pop("text")
            yield {
                "valid": valid,
                "source_image": insight["source"],
                "value": value,
                "data": {"notify": content["notify"], **content},
            }

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return False


class BrandInsightImporter(InsightImporter):
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
    ) -> Iterator[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content["brand_tag"]
            valid = self.is_valid(barcode, value_tag, seen_set)

            insert = {
                "valid": valid,
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


class StoreInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> str:
        return InsightType.store.name

    def is_valid(self, tag: str, seen_set: Set[str]) -> bool:
        return tag not in seen_set

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterator[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content["value_tag"]
            valid = self.is_valid(value_tag, seen_set)

            insert = {
                "valid": valid,
                "value_tag": value_tag,
                "value": content["value"],
                "source_image": insight["source"],
                "data": {"text": content["text"], "notify": content["notify"]},
            }

            if "automatic_processing" in content:
                insert["automatic_processing"] = content["automatic_processing"]

            yield insert
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return False


class PackagingInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> str:
        return InsightType.packaging.name

    def is_valid(self, tag: str, seen_set: Set[str]) -> bool:
        return tag not in seen_set

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterator[JSONType]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            content = insight["content"]
            value_tag = content["packaging_tag"]
            valid = self.is_valid(value_tag, seen_set)

            insert = {
                "valid": valid,
                "value_tag": value_tag,
                "value": content["packaging"],
                "source_image": insight["source"],
                "data": {"text": content["text"], "notify": content["notify"]},
            }

            if "automatic_processing" in content:
                insert["automatic_processing"] = content["automatic_processing"]

            yield insert
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: JSONType) -> bool:
        return False


class LatentInsightImporter(InsightImporter):
    def __init__(self, product_store: ProductStore, insight_type: str):
        super().__init__(product_store)
        self.insight_type: str = insight_type

    def get_type(self) -> str:
        return self.insight_type

    def process_product_insights(
        self, barcode: str, insights: List[JSONType], server_domain: str
    ) -> Iterator[JSONType]:
        for insight in insights:
            content = insight["content"]
            value_tag = content.pop("value_tag", None)
            value = content.pop("value", None)

            yield {
                "valid": False,
                "value_tag": value_tag,
                "value": value,
                "source_image": insight["source"],
                "data": content,
            }


class InsightImporterFactory:
    importers: JSONType = {
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckImporter,
        InsightType.packager_code.name: PackagerCodeInsightImporter,
        InsightType.label.name: LabelInsightImporter,
        InsightType.category.name: CategoryImporter,
        InsightType.product_weight.name: ProductWeightImporter,
        InsightType.expiration_date.name: ExpirationDateImporter,
        InsightType.brand.name: BrandInsightImporter,
        InsightType.store.name: StoreInsightImporter,
        InsightType.packaging.name: PackagingInsightImporter,
        InsightType.image_flag.name: LatentInsightImporter,
        InsightType.nutrient.name: LatentInsightImporter,
        InsightType.nutrient_mention.name: LatentInsightImporter,
        InsightType.location.name: LatentInsightImporter,
    }

    @classmethod
    def create(
        cls, insight_type: str, product_store: ProductStore
    ) -> BaseInsightImporter:
        if insight_type in cls.importers:
            insight_cls = cls.importers[insight_type]

            if insight_cls == LatentInsightImporter:
                return insight_cls(product_store, insight_type)

            return insight_cls(product_store)
        else:
            raise ValueError("unknown insight type: {}".format(insight_type))
