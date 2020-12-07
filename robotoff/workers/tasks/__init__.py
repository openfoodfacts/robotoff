import logging
import multiprocessing
from typing import Callable, Dict

from robotoff.models import db, ProductInsight
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
    "import_image": import_image,
    "download_dataset": download_product_dataset,
    "product_deleted": delete_product_insights,
    "product_updated": update_insights,
    "object_detection": run_object_detection,
    "update_recycling": update_recycling,
}
