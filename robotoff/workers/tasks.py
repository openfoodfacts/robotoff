import logging
import multiprocessing
from typing import Dict, Callable, Optional

from robotoff.elasticsearch.category.predict import (
    predict_from_product as predict_category_from_product_es,
)
from robotoff.ml.category.neural.model import (
    predict_from_product as predict_category_from_product_ml,
)
from robotoff.insights.dataclass import ProductInsights
from robotoff.insights._enum import InsightType
from robotoff.insights.importer import InsightImporterFactory, BaseInsightImporter
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
from robotoff.off import get_product, get_server_type, ServerType
from robotoff.products import (
    has_dataset_changed,
    fetch_dataset,
    get_product_store,
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


def import_image(barcode: str, image_url: str, ocr_url: str, server_domain: str):
    logger.info(
        "Detect insights for product {}, " "image {}".format(barcode, image_url)
    )
    product_store = get_product_store()
    insights_all = get_insights_from_image(barcode, image_url, ocr_url)

    for insight_type, insights in insights_all.items():
        if insight_type == InsightType.image_flag:
            notify_image_flag(
                insights.insights,
                insights.source_image,  # type: ignore
                insights.barcode,
            )
            continue

        logger.info("Extracting {}".format(insight_type))
        importer: BaseInsightImporter = InsightImporterFactory.create(
            insight_type, product_store
        )

        with db.atomic():
            imported, latent_imported = importer.import_insights(
                [insights], server_domain=server_domain, automatic=True
            )
            logger.info(
                "Import finished, {} insights imported, {} latent insights imported".format(
                    imported, latent_imported
                )
            )


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

    update_product_updated_ingredients(barcode, product_dict, server_domain)

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

    product_insights = []
    product_insight = predict_category_from_product_es(product)

    if product_insight is not None:
        product_insights.append(product_insight)

    product_insight = predict_category_from_product_ml(product, filter_blacklisted=True)

    if product_insight is not None:
        product_insights.append(product_insight)

    if not product_insights:
        return False

    merged_product_insight = ProductInsights.merge(product_insights)
    product_store = get_product_store()
    importer = InsightImporterFactory.create(InsightType.category, product_store)

    imported, _ = importer.import_insights(
        [merged_product_insight],
        server_domain=server_domain,
        automatic=False,
        latent=False,
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

    product_store = get_product_store()
    insights_all = get_insights_from_product_name(barcode, product_name)

    for insight_type, insights in insights_all.items():
        importer = InsightImporterFactory.create(insight_type, product_store)
        imported, _ = importer.import_insights(
            [insights], server_domain=server_domain, automatic=False, latent=False
        )

        if imported:
            logger.info(
                "{} insights ({}) imported for product {}".format(
                    imported, insight_type, barcode
                )
            )
            updated = True

    return updated


def update_product_updated_ingredients(
    barcode: str, product: JSONType, server_domain: str
) -> int:
    deleted = 0

    for insight in ProductInsight.select().where(
        ProductInsight.type == InsightType.ingredient_spellcheck.name,
        ProductInsight.annotation.is_null(True),
        ProductInsight.barcode == barcode,
    ):
        lang = insight.data["lang"]
        insight_text = insight.data["text"]
        field_name = "ingredients_text_{}".format(lang)

        if field_name not in product or product[field_name] != insight_text:
            logger.info(
                "Ingredients deleted or updated for product {} (lang: {}), deleting "
                "insight".format(barcode, lang)
            )
            insight.delete_instance()
            deleted += 1

    return deleted


EVENT_MAPPING: Dict[str, Callable] = {
    "import_image": import_image,
    "download_dataset": download_product_dataset,
    "product_deleted": delete_product_insights,
    "product_updated": updated_product_update_insights,
}
