import abc
import datetime
import itertools
import operator
import uuid
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple, Type

from robotoff import settings
from robotoff.brands import BRAND_PREFIX_STORE, in_barcode_range
from robotoff.insights.dataclass import Insight, InsightType
from robotoff.insights.normalize import normalize_emb_code
from robotoff.models import Prediction as PredictionModel
from robotoff.models import ProductInsight, batch_insert
from robotoff.off import get_server_type
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
from robotoff.products import Product, ProductStore, get_product_store, is_valid_image
from robotoff.taxonomy import Taxonomy, TaxonomyNode, get_taxonomy
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.cache import CachedStore

logger = get_logger(__name__)


def load_authorized_labels() -> Set[str]:
    return set(text_file_iter(settings.OCR_LABEL_WHITELIST_DATA_PATH))


AUTHORIZED_LABELS_STORE = CachedStore(load_authorized_labels, expiration_interval=None)


def generate_seen_set_query(
    insight_type: InsightType, barcode: str, server_domain: str
):
    """Get `value` and `value_tag` of all insights for specific product and
    `insight_type`."""
    return ProductInsight.select(ProductInsight.value, ProductInsight.value_tag).where(
        ProductInsight.type == insight_type.name,
        ProductInsight.latent == False,  # noqa: E712
        ProductInsight.barcode == barcode,
        ProductInsight.server_domain == server_domain,
    )


def is_reserved_barcode(barcode: str) -> bool:
    if barcode.startswith("0"):
        barcode = barcode[1:]

    return barcode.startswith("2")


GroupedByBarcodeInsights = Dict[str, List[Insight]]


class InsightImporter(metaclass=abc.ABCMeta):
    """Abstract class for all insight importers."""

    def __init__(self, product_store: ProductStore):
        self.product_store: ProductStore = product_store

    def import_insights(
        self,
        data: Iterable[ProductPredictions],
        server_domain: str,
        automatic: bool,
    ) -> int:
        """Import insights, this is the main method.

        :return: the number of insights that were imported.
        """
        insights: Iterator[Insight] = self.generate_insights(
            data, server_domain, automatic
        )
        return batch_insert(
            ProductInsight, (insight.to_dict() for insight in insights), 50
        )

    def add_fields(
        self,
        insight: Insight,
        product: Optional[Product],
        timestamp: datetime.datetime,
        server_domain: str,
        server_type: str,
    ):
        """Add mandatory insight fields."""
        barcode = insight.barcode
        insight.reserved_barcode = is_reserved_barcode(barcode)
        insight.server_domain = server_domain
        insight.server_type = server_type
        insight.id = str(uuid.uuid4())
        insight.timestamp = timestamp
        insight.countries = getattr(product, "countries_tags", [])
        insight.brands = getattr(product, "brands_tags", [])

        if insight.automatic_processing:
            insight.process_after = timestamp + datetime.timedelta(minutes=10)

    @abc.abstractmethod
    def get_type(self) -> InsightType:
        pass

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        return True

    def get_seen_set(self, barcode: str, server_domain: str) -> Set[str]:
        """Get the set of `value_tag` of all insights for specific product
        and `insight_type`."""
        seen_set: Set[str] = set()
        query = generate_seen_set_query(self.get_type(), barcode, server_domain)

        for t in query.iterator():
            seen_set.add(t.value_tag)

        return seen_set

    def get_seen_count(self, barcode: str, server_domain: str) -> int:
        """Return the number of insights that have the same barcode and
        server domain as provided as parameter."""
        query = generate_seen_set_query(self.get_type(), barcode, server_domain)
        return query.count()

    def generate_insights(
        self,
        data: Iterable[ProductPredictions],
        server_domain: str,
        automatic: bool,
    ) -> Iterator[Insight]:
        """
        Given a set of predictions, generate insights by products based upon those.

        It calls the _generate_insight method, specific to each insight type
        (and implemented in sub-classes)
        """
        timestamp = datetime.datetime.utcnow()
        server_type = get_server_type(server_domain).name
        grouped_by: GroupedByBarcodeInsights = self.group_by_barcode(data)

        for barcode, insights in grouped_by.items():
            insights = self.sort_by_priority(insights)
            product = self.product_store[barcode]

            for insight in self._generate_insights(
                product, barcode, insights, server_domain
            ):
                if not automatic:
                    insight.automatic_processing = False

                elif insight.automatic_processing is None:
                    insight.automatic_processing = not self.need_validation(insight)

                self.add_fields(insight, product, timestamp, server_domain, server_type)
                yield insight

    def group_by_barcode(
        self, data: Iterable[ProductPredictions]
    ) -> GroupedByBarcodeInsights:
        """Generate Insights from ProductPredictions and group them by
        barcode.

        :param data: an iterable of ProductPredictions
        :return: A dict mapping a barcode to a list of Insights
        """
        grouped_by: GroupedByBarcodeInsights = {}
        insight_type = self.get_type()

        for item in data:
            barcode = item.barcode

            if item.type != insight_type:
                raise ValueError("unexpected insight type: '{}'".format(insight_type))

            predictions = item.predictions

            if not predictions:
                continue

            grouped_by.setdefault(barcode, [])

            for prediction in predictions:
                insights = Insight.from_prediction(prediction, item)
                grouped_by[barcode].append(insights)

        return grouped_by

    @staticmethod
    def sort_by_priority(insights: List[Insight]) -> List[Insight]:
        return sorted(insights, key=lambda insight: insight.data.get("priority", 1))

    @abc.abstractmethod
    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        pass


class PackagerCodeInsightImporter(InsightImporter):
    def get_seen_set(self, barcode: str, server_domain: str) -> Set[str]:
        seen_set: Set[str] = set()
        query = generate_seen_set_query(self.get_type(), barcode, server_domain)

        for t in query.iterator():
            seen_set.add(t.value)

        return seen_set

    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packager_code

    @staticmethod
    def ignore_insight(
        product: Optional[Product],
        emb_code: str,
        code_seen: Set[str],
    ) -> bool:
        product_emb_codes_tags = getattr(product, "emb_codes_tags", [])

        normalized_emb_code = normalize_emb_code(emb_code)
        normalized_emb_codes = [normalize_emb_code(c) for c in product_emb_codes_tags]

        if normalized_emb_code in normalized_emb_codes:
            return True

        if emb_code in code_seen:
            return True

        return False

    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set: Set[str] = self.get_seen_set(barcode, server_domain)

        for insight in insights:
            value: str = insight.value  # type: ignore
            if self.ignore_insight(product, value, seen_set):
                continue
            yield insight
            seen_set.add(value)


class LabelInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.label

    @staticmethod
    def ignore_insight(
        product: Optional[Product], tag: str, seen_set: Set[str]
    ) -> bool:
        product_labels_tags = getattr(product, "labels_tags", [])

        if tag in product_labels_tags:
            return True

        if tag in seen_set:
            return True

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
                    return True

        return False

    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore
            if self.ignore_insight(product, value_tag, seen_set):
                continue
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

    def _generate_insights(
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

            if self.ignore_insight(product, value_tag, seen_set):
                continue

            yield insight
            seen_set.add(value_tag)

    def ignore_insight(
        self,
        product: Optional[Product],
        category: str,
        seen_set: Set[str],
    ):
        if product is None:
            logger.debug("Insight for a product which does not exist, ignoring")
            return True  # product not in store !

        product_categories_tags = getattr(product, "categories_tags", [])

        # first check whether this is new information
        if category in product_categories_tags:
            logger.debug(
                "The product already belongs to this category, "
                "considering the insight as invalid"
            )
            return True

        if category in seen_set:
            logger.debug(
                "An insight already exists for this product and "
                "category, considering the insight as invalid"
            )
            return True

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
                    return True

        return False


class ProductWeightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.product_weight

    @staticmethod
    def group_by_subtype(insights: List[Insight]) -> Dict[str, List[Insight]]:
        insights_by_subtype: Dict[str, List[Insight]] = {}

        for insight in insights:
            matcher_type = insight.data["matcher_type"]
            insights_by_subtype.setdefault(matcher_type, [])
            insights_by_subtype[matcher_type].append(insight)

        return insights_by_subtype

    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        if (
            self.get_seen_count(barcode=barcode, server_domain=server_domain)
            or (product and product.quantity is not None)
            or not insights
        ):
            return

        insights_by_subtype = self.group_by_subtype(insights)

        insight_subtype = insights[0].data["matcher_type"]

        multiple_weights = False
        if (
            insight_subtype != "with_mention"
            and len(insights_by_subtype[insight_subtype]) > 1
        ):
            logger.info(
                "{} distinct product weights found for product "
                "{}, aborting import".format(len(insights), barcode)
            )
            multiple_weights = True

        insight = insights[0]
        if multiple_weights:
            # Multiple candidates, don't process automatically
            insight.automatic_processing = False
        yield insight

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        # Validation is needed if the weight was extracted from the product name
        # (not as trustworthy as OCR)
        return insight.data.get("source") == "product_name"


class ExpirationDateImporter(InsightImporter):
    def get_seen_set(self, barcode: str, server_domain: str) -> Set[str]:
        seen_set: Set[str] = set()
        query = generate_seen_set_query(self.get_type(), barcode, server_domain)

        for t in query.iterator():
            seen_set.add(t.value)

        return seen_set

    @staticmethod
    def get_type() -> InsightType:
        return InsightType.expiration_date

    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        if (
            (product and product.expiration_date)
            or self.get_seen_set(barcode=barcode, server_domain=server_domain)
            or not insights
        ):
            return

        date_count = len(set((insight.value for insight in insights)))
        multiple_dates = date_count > 1
        if multiple_dates:
            logger.info(
                "{} distinct expiration dates found for product "
                "{}".format(date_count, barcode)
            )

        insight = insights[0]
        if multiple_dates:
            insight.automatic_processing = False
        yield insight

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        return False


class BrandInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.brand

    def is_valid(self, barcode: str, tag: str) -> bool:
        brand_prefix: Set[Tuple[str, str]] = BRAND_PREFIX_STORE.get()

        if not in_barcode_range(brand_prefix, tag, barcode):
            logger.warn(
                "Barcode {} of brand {} not in barcode " "range".format(barcode, tag)
            )
            return False

        return True

    @staticmethod
    def ignore_insight(
        product: Optional[Product], tag: str, seen_set: Set[str]
    ) -> bool:
        if tag in seen_set:
            return True

        if not product:
            return False

        if product.brands_tags:
            # For now, don't annotate if a brand has already been provided
            return True

        return False

    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore

            if not self.is_valid(barcode, value_tag) or self.ignore_insight(
                product, value_tag, seen_set
            ):
                continue
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

    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore
            if value_tag in seen_set:
                continue
            yield insight
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        return False


class PackagingInsightImporter(InsightImporter):
    @staticmethod
    def get_type() -> InsightType:
        return InsightType.packaging

    def _generate_insights(
        self,
        product: Optional[Product],
        barcode: str,
        insights: List[Insight],
        server_domain: str,
    ) -> Iterator[Insight]:
        seen_set = self.get_seen_set(barcode=barcode, server_domain=server_domain)

        for insight in insights:
            value_tag: str = insight.value_tag  # type: ignore
            if value_tag in seen_set:
                continue
            yield insight
            seen_set.add(value_tag)

    @staticmethod
    def need_validation(insight: Insight) -> bool:
        return False


def is_valid_product_predictions(
    product_predictions: ProductPredictions, product_store: ProductStore
) -> bool:
    """Return True if the ProductPredictions is valid and can be imported,
    i.e:
       - if the source image (if any) is valid
       - if the product was not deleted (only possible to check if the
         ProductStore is backed by the MongoDB)

    :param product_predictions: The ProductPredictions to check
    :param product_store: The ProductStore used to fetch the product
    information
    :return: Whether the ProductPredictions is valid
    """
    product = product_store[product_predictions.barcode]
    if (
        product
        and product_predictions.source_image
        and not is_valid_image(product.images, product_predictions.source_image)
    ):
        logger.info(
            f"Invalid image for product {product.barcode}: {product_predictions.source_image}"
        )
        return False

    if not product and product_store.is_real_time():
        # if product store is in real time, the product does not exist (deleted)
        logger.info(f"Insight of deleted product {product.barcode}")
        return False

    return True


def create_prediction_model(
    prediction: Prediction,
    product_predictions: ProductPredictions,
    server_domain: str,
    timestamp: datetime.datetime,
):
    return {
        "barcode": product_predictions.barcode,
        "type": product_predictions.type.name,
        "data": prediction.data,
        "timestamp": timestamp,
        "value_tag": prediction.value_tag,
        "value": prediction.value,
        "source_image": product_predictions.source_image,
        "automatic_processing": prediction.automatic_processing or False,
        "server_domain": server_domain,
        "predictor": prediction.predictor,
    }


def import_product_predictions(
    barcode: str,
    product_predictions_iter: Iterable[ProductPredictions],
    server_domain: str,
):
    """Import product predictions.

    If a prediction already exists in DB (same (barcode, type, server_domain,
    source_image, value, value_tag)), it won't be imported.

    :param barcode: Barcode of the product. All `product_predictions` must
    have the same barcode.
    :param product_predictions_iter: Iterable of ProductPredictions.
    :param server_domain: The server domain associated with the predictions.
    :return: The number of items imported in DB.
    """
    timestamp = datetime.datetime.utcnow()
    existing_predictions = set(
        PredictionModel.select(
            PredictionModel.type,
            PredictionModel.server_domain,
            PredictionModel.source_image,
            PredictionModel.value_tag,
            PredictionModel.value,
        )
        .where(PredictionModel.barcode == barcode)
        .tuples()
    )

    to_import = itertools.chain.from_iterable(
        (
            (
                create_prediction_model(
                    prediction, product_predictions, server_domain, timestamp
                )
                for prediction in product_predictions.predictions
                if (
                    product_predictions.type,
                    server_domain,
                    product_predictions.source_image,
                    prediction.value_tag,
                    prediction.value,
                )
                not in existing_predictions
            )
            for product_predictions in product_predictions_iter
        )
    )
    return batch_insert(PredictionModel, to_import, 50)


class InsightImporterFactory:
    """Class used to create an InsightImporter.

    InsightImporter classes are responsible for filtering and storing
    insights into the database. The insight import strategy is specific to its
    type.
    """

    importers: Dict[InsightType, Type[InsightImporter]] = {
        InsightType.packager_code: PackagerCodeInsightImporter,
        InsightType.label: LabelInsightImporter,
        InsightType.category: CategoryImporter,
        InsightType.product_weight: ProductWeightImporter,
        InsightType.expiration_date: ExpirationDateImporter,
        InsightType.brand: BrandInsightImporter,
        InsightType.store: StoreInsightImporter,
        InsightType.packaging: PackagingInsightImporter,
    }

    @classmethod
    def create(
        cls, insight_type: InsightType, product_store: ProductStore
    ) -> Optional[InsightImporter]:
        """Create an InsightImporter.

        :param insight_type: the type of the InsightImporter to create
        :param product_store: the ProductStore that will be used to check
        insight validity.
        :return: The InsightImporter or None if no importer is available for
        this `insight_type`.
        """
        if insight_type in cls.importers:
            insight_cls = cls.importers[insight_type]
            return insight_cls(product_store)
        else:
            return None


def import_insights(
    product_predictions: Iterable[ProductPredictions],
    server_domain: str,
    automatic: bool,
    product_store: Optional[ProductStore] = None,
) -> int:
    if product_store is None:
        product_store = get_product_store()

    importers: Dict[InsightType, Optional[InsightImporter]] = {}
    product_predictions = [
        p for p in product_predictions if is_valid_product_predictions(p, product_store)
    ]

    predictions_imported = 0
    for barcode, product_predictions_group in itertools.groupby(
        sorted(product_predictions, key=operator.attrgetter("barcode")),
        operator.attrgetter("barcode"),
    ):
        predictions_imported += import_product_predictions(
            barcode, product_predictions_group, server_domain
        )
    logger.info(f"{predictions_imported} predictions imported")

    prediction_type: PredictionType
    insight_group: Iterable[ProductPredictions]
    imported = 0

    for prediction_type, insight_group in itertools.groupby(
        sorted(product_predictions, key=operator.attrgetter("type")),
        operator.attrgetter("type"),
    ):
        insight_type = InsightType[prediction_type]
        if insight_type not in importers:
            importers[insight_type] = InsightImporterFactory.create(
                insight_type, product_store
            )
        importer = importers[insight_type]
        if importer is not None:
            imported += importer.import_insights(
                insight_group, server_domain, automatic
            )

    return imported
