import json
from typing import List, Dict, Callable

from robotoff.insights.importer import InsightImporterFactory, InsightImporter
from robotoff.insights.ocr import get_insights_from_image
from robotoff.models import db
from robotoff.products import (has_dataset_changed, fetch_dataset,
                               CACHED_PRODUCT_STORE)
from robotoff.utils import get_logger

logger = get_logger(__name__)


def run_task(event_type: str, event_kwargs: Dict) -> None:
    if event_type == 'import_insights':
        func: Callable = import_insights

    elif event_type == 'import_image':
        func = import_image

    elif event_type == 'download_dataset':
        func = download_product_dataset

    else:
        raise ValueError("unknown event type: '{}".format(event_type))

    try:
        func(**event_kwargs)
    except Exception as e:
        logger.error(e, exc_info=1)


def download_product_dataset():
    if has_dataset_changed():
        fetch_dataset()


def import_insights(insight_type: str,
                    items: List[str]):
    importer_cls = InsightImporterFactory.create(insight_type)
    product_store = CACHED_PRODUCT_STORE.get()
    importer: InsightImporter = importer_cls(product_store)

    with db.atomic():
        imported = importer.import_insights((json.loads(l) for l in items))
        logger.info("Import finished, {} insights imported".format(imported))


def import_image(barcode: str, image_url: str, ocr_url: str):
    logger.info("Detect insights for product {}".format(barcode))
    product_store = CACHED_PRODUCT_STORE.get()
    insights_all = get_insights_from_image(barcode, image_url, ocr_url)

    if insights_all is None:
        logger.info("OCR file not found")
        return

    for insight_type, insights in insights_all.items():
        logger.info("Extracting {}".format(insight_type))
        importer_cls = InsightImporterFactory.create(insight_type)
        importer: InsightImporter = importer_cls(product_store)

        with db.atomic():
            imported = importer.import_insights([insights])
            logger.info("Import finished, {} insights imported".format(imported))
