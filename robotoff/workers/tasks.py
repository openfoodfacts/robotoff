import json
import logging
import multiprocessing
from typing import List, Dict, Callable

from robotoff.insights._enum import InsightType
from robotoff.insights.importer import InsightImporterFactory, InsightImporter
from robotoff.insights.ocr import get_insights_from_image
from robotoff.models import db, ProductInsight
from robotoff.products import (has_dataset_changed, fetch_dataset,
                               CACHED_PRODUCT_STORE)
from robotoff.slack import notify_image_flag
from robotoff.utils import get_logger, configure_root_logger

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


def import_insights(insight_type: str,
                    items: List[str]):
    product_store = CACHED_PRODUCT_STORE.get()
    importer: InsightImporter = InsightImporterFactory.create(insight_type,
                                                              product_store)

    with db.atomic():
        imported = importer.import_insights((json.loads(l) for l in items),
                                            automatic=False)
        logger.info("Import finished, {} insights imported".format(imported))


def import_image(barcode: str, image_url: str, ocr_url: str):
    logger.info("Detect insights for product {}, "
                "image {}".format(barcode, image_url))
    product_store = CACHED_PRODUCT_STORE.get()
    insights_all = get_insights_from_image(barcode, image_url, ocr_url)

    if insights_all is None:
        logger.info("OCR file not found")
        return

    for insight_type, insights in insights_all.items():
        if insight_type == InsightType.image_flag.name:
            notify_image_flag(insights['insights'],
                              insights['source'],
                              insights['barcode'])
            continue

        logger.info("Extracting {}".format(insight_type))
        importer: InsightImporter = InsightImporterFactory.create(insight_type,
                                                                  product_store)

        with db.atomic():
            imported = importer.import_insights([insights], automatic=True)
            logger.info("Import finished, {} insights imported".format(imported))


def delete_product_insights(barcode: str):
    logger.info("Product {} deleted, deleting associated "
                "insights...".format(barcode))
    with db.atomic():
        deleted = (ProductInsight.delete()
                   .where(ProductInsight.barcode == barcode).execute())

    logger.info("{} insights deleted".format(deleted))


def updated_product_update_insights(barcode: str):
    logger.info("Product {} updated".format(barcode))


EVENT_MAPPING: Dict[str, Callable] = {
    'import_insights': import_insights,
    'import_image': import_image,
    'download_dataset': download_product_dataset,
    'product_deleted': delete_product_insights,
    'product_updated': updated_product_update_insights,
}
