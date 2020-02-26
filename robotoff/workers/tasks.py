import json
import logging
import multiprocessing
from typing import List, Dict, Callable, Optional

from robotoff.elasticsearch.category.predict import (
    predict_from_product as predict_category_from_product_es,
)
from robotoff.ml.category.neural.model import (
    predict_from_product as predict_category_from_product_ml,
)
from robotoff.insights._enum import InsightType
from robotoff.insights.importer import InsightImporterFactory, InsightImporter
from robotoff.insights.extraction import (
    get_insights_from_image,
    get_insights_from_product_name,
)
from robotoff.insights.validator import (
    delete_invalid_insight,
    InsightValidator,
    InsightValidatorFactory,
)
from robotoff.models import db, ProductInsight
from robotoff.off import get_product, get_server_type, move_to, ServerType
from robotoff.products import (
    has_dataset_changed,
    fetch_dataset,
    CACHED_PRODUCT_STORE,
    Product,
)
from robotoff.slack import notify_image_flag
from robotoff.utils import get_logger, configure_root_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)
root_logger = multiprocessing.get_logger()

if root_logger.level == logging.NOTSET:
    configure_root_logger(root_logger)


def run_task(event_type: str, event_kwargs: Dict) -> None:
    if event_type not in EVENT_MAPPING:
        raise ValueError("unknown event type: '{}".format(event_type))

    func = EVENT_MAPPING[event_type]

    try:
        func(**event_kwargs)
    except Exception as e:
        logger.error(e, exc_info=1)


def download_product_dataset():
    if has_dataset_changed():
        fetch_dataset()


def import_insights(insight_type: str, items: List[str], server_domain: str):
    product_store = CACHED_PRODUCT_STORE.get()
    importer: InsightImporter = InsightImporterFactory.create(
        insight_type, product_store
    )

    with db.atomic():
        imported = importer.import_insights(
            (json.loads(l) for l in items), server_domain=server_domain, automatic=False
        )
        logger.info("Import finished, {} insights imported".format(imported))


def import_image(barcode: str, image_url: str, ocr_url: str, server_domain: str):
    logger.info(
        "Detect insights for product {}, " "image {}".format(barcode, image_url)
    )
    product_store = CACHED_PRODUCT_STORE.get()
    insights_all = get_insights_from_image(barcode, image_url, ocr_url)

    if insights_all is None:
        return

    for insight_type, insights in insights_all.items():
        if insight_type == InsightType.image_flag.name:
            handle_image_flag_insights(insights)
            continue

        logger.info("Extracting {}".format(insight_type))
        importer: InsightImporter = InsightImporterFactory.create(
            insight_type, product_store
        )

        with db.atomic():
            imported = importer.import_insights(
                [insights], server_domain=server_domain, automatic=True
            )
            logger.info("Import finished, {} insights imported".format(imported))


def handle_image_flag_insights(insights: JSONType):
    source = insights["source"]
    barcode = insights["barcode"]
    insights_: List[JSONType] = insights["insights"]

    for insight in insights_:
        insight_subtype = insight["type"]

        if insight_subtype == "text":
            if insight["label"] == "beauty":
                moved = False
                # moved = move_to(barcode, ServerType.obf)

                if moved:
                    insight["moved"] = "obf"
                    logger.info("Product {} moved to OBF".format(barcode))

    notify_image_flag(insights_, source, barcode)


def delete_product_insights(barcode: str, server_domain: str):
    logger.info(
        "Product {} deleted, deleting associated " "insights...".format(barcode)
    )
    with db.atomic():
        deleted = (
            ProductInsight.delete()
            .where(
                ProductInsight.barcode == barcode,
                ProductInsight.annotation.is_null(),
                ProductInsight.server_domain == server_domain,
            )
            .execute()
        )

    logger.info("{} insights deleted".format(deleted))


def updated_product_update_insights(barcode: str, server_domain: str):
    product_dict = get_product(barcode)

    if product_dict is None:
        logger.warn("Updated product does not exist: {}".format(barcode))
        return

    updated = updated_product_predict_insights(barcode, product_dict, server_domain)

    if updated:
        logger.info("Product {} updated".format(barcode))

    product = Product(product_dict)
    validators: Dict[str, Optional[InsightValidator]] = {}

    for insight in (
        ProductInsight.select()
        .where(
            ProductInsight.annotation.is_null(),
            ProductInsight.barcode == barcode,
            ProductInsight.server_domain == server_domain,
        )
        .iterator()
    ):
        if insight.type not in validators:
            validators[insight.type] = InsightValidatorFactory.create(
                insight.type, None
            )

        validator = validators[insight.type]

        if validator is not None:
            insight_deleted = delete_invalid_insight(
                insight, validator=validator, product=product
            )
            if insight_deleted:
                logger.info(
                    "Insight {} deleted (type: {})".format(insight.id, insight.type)
                )


def updated_product_add_category_insight(
    barcode: str, product: JSONType, server_domain: str
) -> bool:
    if get_server_type(server_domain) != ServerType.off:
        return False

    insights = []
    insight = predict_category_from_product_es(product)

    if insight is not None:
        insights.append(insight)

    insights += predict_category_from_product_ml(product, filter_blacklisted=True)

    if not insights:
        return False

    product_store = CACHED_PRODUCT_STORE.get()
    importer = InsightImporterFactory.create(InsightType.category.name, product_store)

    imported = importer.import_insights(
        insights, server_domain=server_domain, automatic=False
    )

    if imported:
        logger.info("Category insight imported for product {}".format(barcode))

    return bool(imported)


def updated_product_predict_insights(
    barcode: str, product: JSONType, server_domain: str
) -> bool:
    updated = updated_product_add_category_insight(barcode, product, server_domain)
    product_name = product.get("product_name")

    if not product_name:
        return updated

    product_store = CACHED_PRODUCT_STORE.get()
    insights_all = get_insights_from_product_name(barcode, product_name)

    for insight_type, insights in insights_all.items():
        importer = InsightImporterFactory.create(insight_type, product_store)
        imported = importer.import_insights(
            [insights], server_domain=server_domain, automatic=False
        )

        if imported:
            logger.info(
                "{} insights ({}) imported for product {}".format(
                    imported, insight_type, barcode
                )
            )
            updated = True

    return updated


EVENT_MAPPING: Dict[str, Callable] = {
    "import_insights": import_insights,
    "import_image": import_image,
    "download_dataset": download_product_dataset,
    "product_deleted": delete_product_insights,
    "product_updated": updated_product_update_insights,
}
