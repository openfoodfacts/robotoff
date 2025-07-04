from robotoff.images import delete_images
from robotoff.insights.extraction import get_predictions_from_product_name
from robotoff.insights.importer import import_insights, refresh_insights
from robotoff.models import with_db
from robotoff.products import get_product
from robotoff.redis import Lock, LockedResourceException
from robotoff.types import JSONType, ProductIdentifier
from robotoff.utils import get_logger
from robotoff.workers.tasks.common import add_category_insight

logger = get_logger(__name__)


@with_db
def update_insights_job(product_id: ProductIdentifier, diffs: JSONType) -> None:
    """This job is triggered by the webhook API, when product information has
    been updated.

    When a product is updated, Robotoff will:

    1. Generate new predictions related to the product's category and name.
    2. Regenerate all insights from the product associated predictions.

    :param product_id: identifier of the product
    :param diffs: a dict containing a diff of the update, the format is
      defined by Product Opener
    """
    logger.info("Running `update_insights` for %s", product_id)

    # Check for valid product identifier
    if not product_id.is_valid():
        logger.info("Invalid product identifier received, skipping product update")
        return

    try:
        with Lock(
            name=f"robotoff:product_update_job:{product_id.server_type.name}:{product_id.barcode}",
            expire=300,
            timeout=10,
        ):
            # We handle concurrency thanks to the lock as the task will fetch
            # product from MongoDB at the time it runs, it's not worth
            # reprocessing with another task arriving concurrently.
            # The expire is there only in case the lock is not released
            # (process killed)
            deleted_images = diffs.get("uploaded_images", {}).get("delete")
            if deleted_images:
                # deleted_images is a list of image IDs that have been deleted
                logger.info("images deleted: %s, launching DB update", deleted_images)
                delete_images(product_id, deleted_images)

            product_dict = get_product(product_id)

            if product_dict is None:
                logger.info("Updated product does not exist: %s", product_id)
                return

            updated_product_predict_insights(product_id, product_dict, diffs=diffs)
            logger.info("Refreshing insights...")
            import_results = refresh_insights(product_id)
            for import_result in import_results:
                logger.info(import_result)
    except LockedResourceException:
        logger.info(
            "Couldn't acquire product_update lock, skipping product_update for product %s",
            product_id,
        )


def should_rerun_category_predictor(diffs: JSONType | None) -> bool:
    """Check if the category predictor should be rerun based on the update diffs.

    :param diffs: a dict containing a diff of the update, the format is
        defined by Product Opener. This is used to determine whether we
        should run the category predictor again or not, depending on the
        changes made to the product.
    :return: True if the category predictor should be rerun, False otherwise.
    """
    if diffs is None:
        return True

    fields_to_check = ["product_name", "ingredients_text"]
    fields = diffs.get("fields", {})
    updated_fields = fields.get("change", [])
    added_fields = fields.get("add", [])
    has_nutriments_change = "nutriments" in diffs
    uploaded_images = diffs.get("uploaded_images", {})
    is_uploaded_image = "add" in uploaded_images
    is_deleted_image = "delete" in uploaded_images
    # Check if any of the fields that affect category prediction have changed
    return (
        has_nutriments_change
        or is_uploaded_image
        or is_deleted_image
        or any(key in updated_fields for key in fields_to_check)
        or any(key in added_fields for key in fields_to_check)
    )


def updated_product_predict_insights(
    product_id: ProductIdentifier,
    product: JSONType,
    triton_uri: str | None = None,
    diffs: JSONType | None = None,
) -> None:
    """Predict and import category insights and insights-derived from product
    name.

    :param product_id: identifier of the product
    :param product: product as retrieved from MongoDB
    :param triton_uri: URI of the Triton Inference Server, defaults to
        None. If not provided, the default value from settings is used.
    :param diffs: a dict containing a diff of the update, the format is
        defined by Product Opener. This is used to determine whether we
        should run the category predictor again or not, depending on the
        changes made to the product.
    """
    if should_rerun_category_predictor(diffs):
        add_category_insight(product_id, product, triton_uri=triton_uri)

    product_name = product.get("product_name")

    if not product_name:
        return

    if product_id.server_type.is_food():
        # Only available for food products for now
        logger.info("Generating predictions from product name...")
        predictions_all = get_predictions_from_product_name(product_id, product_name)
        import_result = import_insights(predictions_all, product_id.server_type)
        logger.info(import_result)
