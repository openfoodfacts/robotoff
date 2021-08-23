import logging
import multiprocessing
from typing import Callable, Dict

from robotoff.models import ProductInsight, db
from robotoff.products import fetch_dataset, has_dataset_changed
from robotoff.utils import configure_root_logger, get_logger

from .import_image import import_image, run_object_detection
from .product_updated import update_insights
from .update_recycle import update_recycling

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


EVENT_MAPPING: Dict[str, Callable] = {
    # 'import_image' is triggered every time there is a new OCR image available for processing by Robotoff, via /api/v1/images/import.
    #
    # On each image import, Robotoff performs the following tasks:
    #  1. Generates various insights based on the OCR-extracted text from the image.
    #  2. Extracts the nutriscore insight based on the nutriscore ML model.
    #  3. Triggers the 'object_detection' task, which is described below.
    #  4. Stores the imported image metadata in the Robotoff DB.
    #
    "import_image": import_image,
    # 'download_dataset' is triggered via /api/v1/products/dataset and causes Robotoff to re-import the Product Opener product dump.
    #
    "download_dataset": download_product_dataset,
    # 'product_deleted' is triggered by Product Opener via /api/v1/webhook/product when the given product has been removed from the
    # database - in this case we must delete all of the associated insights that have not been annotated.
    #
    "product_deleted": delete_product_insights,
    # 'product_updated' is similarly triggered by the webhook API, when product information has been updated.
    #
    # When a product is updated, Robotoff will:
    # 1. Generate new insights related to the product's category and name.
    # 2. Clean up any unvalidated existing insights that no longer apply to the product.
    #
    "product_updated": update_insights,
    # 'object_detection' consists of logo detection: extracting logos from product images and generating logo-related insights.
    # This task is triggered by the 'import_image' task above.
    #
    "object_detection": run_object_detection,
    # 'update_recycling' auto-selects the recycling photos for a given product.
    # NOTE: currently this task is not being triggered from anywhere.
    #
    "update_recycling": update_recycling,
}
