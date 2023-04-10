from robotoff.insights.importer import refresh_insights
from robotoff.models import Prediction, ProductInsight, with_db
from robotoff.products import fetch_dataset, has_dataset_changed
from robotoff.types import ProductIdentifier
from robotoff.utils import get_logger

from .import_image import run_import_image_job  # noqa: F401
from .product_updated import update_insights_job  # noqa: F401

logger = get_logger(__name__)


@with_db
def download_product_dataset_job():
    """This job is triggered via /api/v1/products/dataset and causes Robotoff
    to re-import the Product Opener product dump."""
    if has_dataset_changed():
        fetch_dataset()


@with_db
def delete_product_insights_job(product_id: ProductIdentifier):
    """This job is triggered by Product Opener via /api/v1/webhook/product
    when the given product has been removed from the database - in this case
    we must delete all of the associated predictions and insights that have
    not been annotated.
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
        f"{deleted_predictions} predictions deleted, "
        f"{deleted_insights} insights deleted"
    )


@with_db
def refresh_insights_job(product_ids: list[ProductIdentifier]):
    logger.info(f"Refreshing insights for {len(product_ids)} products")
    for product_id in product_ids:
        import_results = refresh_insights(product_id)
        for import_result in import_results:
            logger.info(import_result)
