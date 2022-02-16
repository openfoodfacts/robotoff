import logging
import multiprocessing
from typing import Callable, Dict

from robotoff.models import Prediction, ProductInsight, db, with_db
from robotoff.products import fetch_dataset, has_dataset_changed
from robotoff.utils import configure_root_logger, get_logger

from .import_image import run_import_image_job
from .product_updated import update_insights
from .update_recycle import update_recycling

logger = get_logger(__name__)
root_logger = multiprocessing.get_logger()

if root_logger.level == logging.NOTSET:
    configure_root_logger(root_logger)


def run_task(event_type: str, event_kwargs: Dict) -> None:
    if event_type not in EVENT_MAPPING:
        raise ValueError(f"unknown event type: '{event_type}")

    func = EVENT_MAPPING[event_type]

    try:
        # we run task inside transaction to avoid side effects
        with db:
            with db.atomic():
                func(**event_kwargs)
    except Exception as e:
        logger.error(e, exc_info=1)


@with_db
def download_product_dataset():
    if has_dataset_changed():
        fetch_dataset()


@with_db
def delete_product_insights(barcode: str, server_domain: str):
    logger.info(f"Product {barcode} deleted, deleting associated insights...")
    deleted_predictions = (
        Prediction.delete()
        .where(
            Prediction.barcode == barcode,
            Prediction.server_domain == server_domain,
        )
        .execute()
    )
    deleted_insights = (
        ProductInsight.delete()
        .where(
            ProductInsight.barcode == barcode,
            ProductInsight.annotation.is_null(),
            ProductInsight.server_domain == server_domain,
        )
        .execute()
    )

    logger.info(
        f"{deleted_predictions} predictions deleted, "
        f"{deleted_insights} insights deleted"
    )


EVENT_MAPPING: Dict[str, Callable] = {
    # 'import_image' is triggered every time there is a new OCR image available for processing by Robotoff, via /api/v1/images/import.
    #
    # On each image import, Robotoff performs the following tasks:
    #  1. Generates various predictions based on the OCR-extracted text from the image.
    #  2. Extracts the nutriscore prediction based on the nutriscore ML model.
    #  3. Triggers the 'object_detection' task, which is described below.
    #  4. Stores the imported image metadata in the Robotoff DB.
    #
    "import_image": run_import_image_job,
    # 'download_dataset' is triggered via /api/v1/products/dataset and causes Robotoff to re-import the Product Opener product dump.
    #
    "download_dataset": download_product_dataset,
    # 'product_deleted' is triggered by Product Opener via /api/v1/webhook/product when the given product has been removed from the
    # database - in this case we must delete all of the associated predictions and insights that have not been annotated.
    #
    "product_deleted": delete_product_insights,
    # 'product_updated' is similarly triggered by the webhook API, when product information has been updated.
    #
    # When a product is updated, Robotoff will:
    # 1. Generate new predictions related to the product's category and name.
    # 2. Regenerate all insights from the product associated predictions.
    #
    "product_updated": update_insights,
    # 'update_recycling' auto-selects the recycling photos for a given product.
    # NOTE: currently this task is not being triggered from anywhere.
    #
    "update_recycling": update_recycling,
}
