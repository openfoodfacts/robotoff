import abc
import copy
import datetime
import uuid
from typing import Dict, Iterable, Iterator, List, Set, Optional, Tuple, Type

from more_itertools import chunked

from robotoff.brands import BRAND_PREFIX_STORE, in_barcode_range, BRAND_BLACKLIST_STORE
from robotoff.insights.dataclass import Insight, ProductInsights
from robotoff.insights._enum import InsightType
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import batch_insert, LatentProductInsight, ProductInsight
from robotoff.off import get_server_type
from robotoff.products import is_valid_image, ProductStore, Product
from robotoff import settings
from robotoff.taxonomy import Taxonomy, TaxonomyNode, get_taxonomy
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.cache import CachedStore
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def load_authorized_labels() -> Set[str]:
    return set(text_file_iter(settings.OCR_LABEL_WHITELIST_DATA_PATH))


AUTHORIZED_LABELS_STORE = CachedStore(load_authorized_labels, expiration_interval=None)


def generate_seen_set_query(
    insight_type: InsightType, barcode: str, server_domain: str
):
    return ProductInsight.select(ProductInsight.value_tag).where(
        ProductInsight.type == insight_type.name,
        ProductInsight.barcode == barcode,
        ProductInsight.server_domain == server_domain,
    )


def is_reserved_barcode(barcode: str) -> bool:
    if barcode.startswith("0"):
        barcode = barcode[1:]

    return barcode.startswith("2")


def generate_insight_dict(insight: Insight) -> JSONType:
    insight_dict = insight.to_dict()
    insight_dict.pop("valid")
    return insight_dict


def generate_latent_insight(insight: JSONType, valid: bool) -> JSONType:
    insight = copy.deepcopy(insight)
    insight.pop("automatic_processing")
    insight.pop("reserved_barcode")
    insight.pop("countries")
    insight.pop("brands")
    insight.setdefault("data", {})
    insight["data"]["valid"] = valid
    return insight


def exist_latent(latent_insight: JSONType) -> bool:
    return LatentProductInsight.exists(
        barcode=latent_insight["barcode"],
        insight_type=latent_insight["type"],
        server_domain=latent_insight["server_domain"],
        value_tag=latent_insight.get("value_tag"),
        value=latent_insight.get("value"),
        source_image=latent_insight.get("source_image"),
    )


class BaseInsightImporter(metaclass=abc.ABCMeta):
    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    def import_insights(
        self,
        data: Iterable[ProductInsights],
        server_domain: str,
        automatic: bool,
        latent: bool = True,
    ) -> Tuple[int, int]:
        timestamp = datetime.datetime.utcnow()
        processed_insights: Iterator[Insight] = self.process_insights(
            data, server_domain, automatic
        )
        full_insights = self.add_fields(processed_insights, timestamp, server_domain)
        inserted = 0
        latent_inserted = 0

        for raw_insight_batch in chunked(full_insights, 50):
            insight_batch: List[JSONType] = []
            latent_batch: List[JSONType] = []
            insight: Insight

            for insight in raw_insight_batch:
                valid = insight.valid
                insight_dict = generate_insight_dict(insight)
                latent_insight = generate_latent_insight(insight_dict, valid)
                latent_exist = exist_latent(latent_insight)

                if valid:
                    insight_batch.append(insight_dict)
                    # if insight is valid, always add it to latent insights
                    if not latent_exist:
                        latent_batch.append(latent_insight)

                elif latent and not latent_exist:
                    # invalid insight, only import is as latent if latent = True
                    latent_batch.append(latent_insight)

            inserted += batch_insert(ProductInsight, insight_batch, 50)
            latent_inserted += batch_insert(LatentProductInsight, latent_batch, 50)

        return inserted, latent_inserted

    @abc.abstractmethod
    def process_insights(
        self, data: Iterable[ProductInsights], server_domain: str, automatic: bool
    ) -> Iterator[Insight]:
        pass

    def add_fields(
        self,
        insights: Iterator[Insight],
        timestamp: datetime.datetime,
        server_domain: str,
    ) -> Iterator[Insight]:
        """Add mandatory insight fields."""
        server_type: str = get_server_type(server_domain).name

        for insight in insights:
            barcode = insight.barcode
            product = self.product_store[barcode]
            insight.reserved_barcode = is_reserved_barcode(barcode)
            insight.server_domain = server_domain
            insight.server_type = server_type
            insight.id = str(uuid.uuid4())
            insight.timestamp = timestamp
            insight.countries = getattr(product, "countries_tags", [])
            insight.brands = getattr(product, "brands_tags", [])
            yield insight

    @abc.abstractmethod
    def get_type(self) -> InsightType:
        pass

    @staticmethod
    def need_validation(insight: Insight) -> bool:
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
    def get_type() -> InsightType:
        return InsightType.ingredient_spellcheck

    def process_insights(
        self,
        data: Iterable[ProductInsights],
        server_domain: str,
        automatic: bool = False,
    ) -> Iterator[Insight]:
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

        for product_insights in data:
            barcode = product_insights.barcode

            for insight in product_insights.insights:
                lang = insight.data["lang"]
                key = (barcode, lang)

                if key not in seen_set:
                    seen_set.add(key)
                else:
                    continue

                yield Insight.from_raw_insight(insight, product_insights, valid=True)


GroupedByOCRInsights = Dict[str, List[Insight]]


class InsightImporter(BaseInsightImporter, metaclass=abc.ABCMeta):
    def process_insights(
        self, data: Iterable[ProductInsights], server_domain: str, automatic: bool
    ) -> Iterator[Insight]:
        grouped_by: GroupedByOCRInsights = self.group_by_barcode(data)

        for barcode, insights in grouped_by.items():
            insights = self.sort_by_priority(insights)
            product = self.product_store[barcode]
            yield from self._process_product_insights(
                product, barcode, insights, automatic, server_domain
            )

    def _process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        automatic: bool,
        server_domain: str,
    ) -> Iterator[Insight]:
        for insight in self.process_product_insights(
            product, barcode, insights, server_domain
        ):
            source_image: Optional[str] = insight.source_image
            if (
                product
                and source_image
                and not is_valid_image(product.images, source_image)
            ):
                logger.info(
                    "Invalid image for product {}: {}".format(barcode, source_image)
                )
                continue

            if not product and self.product_store.is_real_time():
                # if product store is in real time, the product does not exist (deleted)
                logger.info("Insight of deleted product {}".format(barcode))
                continue

            if not automatic:
                insight.automatic_processing = False

            elif insight.automatic_processing is None:
                insight.automatic_processing = not self.need_validation(insight)

            yield insight

    def group_by_barcode(self, data: Iterable[ProductInsights]) -> GroupedByOCRInsights:
        grouped_by: GroupedByOCRInsights = {}
        insight_type = self.get_type()

        for item in data:
            barcode = item.barcode

            if item.type != insight_type:
                raise ValueError(
                    "unexpected insight type: " "'{}'".format(insight_type)
                )

            raw_insights = item.insights

            if not raw_insights:
                continue

            grouped_by.setdefault(barcode, [])

            for raw_insight in raw_insights:
                insights = Insight.from_raw_insight(raw_insight, item, valid=False)
                grouped_by[barcode].append(insights)

        return grouped_by

    @staticmethod
    def sort_by_priority(insights: List[Insight]) -> List[Insight]:
        return sorted(insights, key=lambda insight: insight.data.get("priority", 1))

    @abc.abstractmethod
    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        pass


class PackagerCodeInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packager_code

    def is_valid(
        self,
        product: Optional[Product],
        barcode: str,
        emb_code: str,
        code_seen: Set[str],
    ) -> bool:
        product_emb_codes_tags = getattr(product, "emb_codes_tags", [])

        normalized_emb_code = normalize_emb_code(emb_code)
        normalized_emb_codes = [normalize_emb_code(c) for c in product_emb_codes_tags]

        if normalized_emb_code in normalized_emb_codes:
            return False

        if emb_code in code_seen:
            return False

        return True

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
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
            value: str = insight.value  # type: ignore
            insight.valid = self.is_valid(product, insight.barcode, value, seen_set)
            yield insight
            seen_set.add(value)

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        if insight.data["type"] in ("eu_fr", "eu_de", "fr_emb", "fishing"):
            return False

        return True


class LabelInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.label

    def is_valid(
        self, product: Optional[Product], barcode: str, tag: str, seen_set: Set[str]
    ) -> bool:
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
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore
            insight.valid = self.is_valid(product, barcode, value_tag, seen_set)
            yield insight
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        authorized_labels: Set[str] = AUTHORIZED_LABELS_STORE.get()

        if insight.value_tag in authorized_labels:
            return False

        return True


class CategoryImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.category

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set: Set[str] = self.get_seen_set(
            barcode=barcode, server_domain=server_domain
        )

        for insight in insights:
            barcode = insight.barcode
            value_tag: str = insight.value_tag  # type: ignore

            insight.valid = self.is_valid(product, barcode, value_tag, seen_set)

            if not insight.valid:
                continue

            yield insight
            seen_set.add(value_tag)

    def is_valid(
        self,
        product: Optional[Product],
        barcode: str,
        category: str,
        seen_set: Set[str],
    ):
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
    def get_type() -> InsightType:
        return InsightType.product_weight

    def is_valid(
        self, product: Optional[Product], barcode: str, weight_value_str: str
    ) -> bool:
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

        if not product:
            return True

        if product.quantity is not None:
            logger.debug("Product quantity field is not null, returning non valid")
            return False

        return True

    @staticmethod
    def group_by_subtype(insights: List[Insight],) -> Dict[str, List[Insight]]:
        insights_by_subtype: Dict[str, List[Insight]] = {}

        for insight in insights:
            matcher_type = insight.data["matcher_type"]
            insights_by_subtype.setdefault(matcher_type, [])
            insights_by_subtype[matcher_type].append(insight)

        return insights_by_subtype

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        if not insights:
            return

        insights_by_subtype = self.group_by_subtype(insights)

        insight = insights[0]
        insight_subtype = insight.data["matcher_type"]

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

        insight.valid = (
            self.is_valid(product, barcode, insight.data["value"]) and not all_invalid
        )
        yield insight

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        # Validation is needed if the weight was extracted from the product name
        # (not as trustworthy as OCR)
        return insight.data.get("source") == "product_name"


class ExpirationDateImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.expiration_date

    def is_valid(self, product: Optional[Product], barcode: str) -> bool:
        if not product:
            return True

        if product.expiration_date:
            logger.debug(
                "Product expiration date field is not null, returning non valid"
            )
            return False

        return True

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
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
            insight.valid = self.is_valid(product, barcode) and not all_invalid
            yield insight

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        return False


class BrandInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.brand

    def is_valid(
        self, product: Optional[Product], barcode: str, tag: str, seen_set: Set[str]
    ) -> bool:
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

        if not product:
            return True

        if product.brands_tags:
            # For now, don't annotate if a brand has already been provided
            return False

        return True

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore
            insight.valid = self.is_valid(product, barcode, value_tag, seen_set)
            yield insight
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        # Validation is needed if the weight was extracted from the product name
        # (not as trustworthy as OCR)
        return insight.data.get("source") == "product_name"


class StoreInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.store

    def is_valid(
        self, product: Optional[Product], tag: str, seen_set: Set[str]
    ) -> bool:
        return tag not in seen_set

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore
            insight.valid = self.is_valid(product, value_tag, seen_set)
            yield insight
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        return False


class PackagingInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packaging

    def is_valid(
        self, product: Optional[Product], tag: str, seen_set: Set[str]
    ) -> bool:
        return tag not in seen_set

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore
            insight.valid = self.is_valid(product, value_tag, seen_set)
            yield insight
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        return False


class LatentInsightImporter(InsightImporter):
    def __init__(self, product_store: ProductStore, insight_type: InsightType):
        super().__init__(product_store)
        self.insight_type: InsightType = insight_type

    def get_type(self) -> InsightType:
        return self.insight_type

    def process_product_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        for insight in insights:
            insight.valid = False
            yield insight


class InsightImporterFactory:
    importers: Dict[InsightType, Type[BaseInsightImporter]] = {
        InsightType.ingredient_spellcheck: IngredientSpellcheckImporter,
        InsightType.packager_code: PackagerCodeInsightImporter,
        InsightType.label: LabelInsightImporter,
        InsightType.category: CategoryImporter,
        InsightType.product_weight: ProductWeightImporter,
        InsightType.expiration_date: ExpirationDateImporter,
        InsightType.brand: BrandInsightImporter,
        InsightType.store: StoreInsightImporter,
        InsightType.packaging: PackagingInsightImporter,
        InsightType.image_flag: LatentInsightImporter,
        InsightType.nutrient: LatentInsightImporter,
        InsightType.nutrient_mention: LatentInsightImporter,
        InsightType.location: LatentInsightImporter,
        InsightType.image_lang: LatentInsightImporter,
        InsightType.image_orientation: LatentInsightImporter,
    }

    @classmethod
    def create(
        cls, insight_type: InsightType, product_store: ProductStore
    ) -> BaseInsightImporter:
        if insight_type in cls.importers:
            insight_cls = cls.importers[insight_type]

            if insight_cls == LatentInsightImporter:
                return insight_cls(product_store, insight_type)  # type: ignore

            return insight_cls(product_store)
        else:
            raise ValueError("unknown insight type: {}".format(insight_type))
