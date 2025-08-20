import logging

from robotoff.insights.importer import refresh_insights
from robotoff.models import Prediction, ProductInsight, with_db
from robotoff.products import fetch_jsonl_dataset, has_jsonl_dataset_changed
from robotoff.types import ProductIdentifier

from .import_image import run_import_image_job  # noqa: F401
from .product_updated import update_insights_job  # noqa: F401

logger = logging.getLogger(__name__)


@with_db
def download_product_dataset_job():
    """This job is triggered via /api/v1/products/dataset and causes Robotoff
    to re-import the Product Opener product dump."""
    if has_jsonl_dataset_changed():
        fetch_jsonl_dataset()


@with_db
def delete_product_insights_job(product_id: ProductIdentifier):
    """This job is triggered by a `deleted` event on Redis Stream,
    when the given product has been removed from the database.

    In this case, we must delete all the associated predictions and insights
    that have not been annotated.
    """
    logger.info("%s deleted, deleting associated insights...", product_id)
    deleted_predictions = (
        Prediction.delete()
        .where(
            Prediction.barcode == product_id.barcode,
            Prediction.server_type == product_id.server_type.name,
        )
        .execute()
    )
    deleted_insights = (
        ProductInsight.delete()
        .where(
            ProductInsight.barcode == product_id.barcode,
            ProductInsight.server_type == product_id.server_type.name,
            ProductInsight.annotation.is_null(),
        )
        .execute()
    )

    logger.info(
        "%s predictions deleted, %s insights deleted",
        deleted_predictions,
        deleted_insights,
    )


@with_db
def refresh_insights_job(product_ids: list[ProductIdentifier]):
    logger.info("Refreshing insights for %s products", len(product_ids))
    for product_id in product_ids:
        import_results = refresh_insights(product_id)
        for import_result in import_results:
            logger.info(import_result)
