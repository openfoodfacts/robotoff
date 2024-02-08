import requests

from robotoff.images import delete_images
from robotoff.insights.extraction import get_predictions_from_product_name
from robotoff.insights.importer import import_insights, refresh_insights
from robotoff.models import with_db
from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.products import get_product
from robotoff.redis import Lock, LockedResourceException
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.types import JSONType, ProductIdentifier
from robotoff.utils import get_logger

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

            updated_product_predict_insights(product_id, product_dict)
            logger.info("Refreshing insights...")
            import_results = refresh_insights(product_id)
            for import_result in import_results:
                logger.info(import_result)
    except LockedResourceException:
        logger.info(
            "Couldn't acquire product_update lock, skipping product_update for product %s",
            product_id,
        )


def add_category_insight(
    product_id: ProductIdentifier, product: JSONType, triton_uri: str | None = None
) -> None:
    """Predict categories for product and import predicted category insight.

    :param product_id: identifier of the product
    :param product: product as retrieved from MongoDB
    :param triton_uri: URI of the Triton Inference Server, defaults to
        None. If not provided, the default value from settings is used.
    """
    if not product_id.server_type.is_food():
        # Category prediction is only available for Food products
        logger.info(
            "`server_type=%s`, skipping category prediction", product_id.server_type
        )
        return

    # predict category using neural model
    try:
        neural_predictions, _ = CategoryClassifier(
            get_taxonomy(TaxonomyType.category.name)
        ).predict(product, product_id, triton_uri=triton_uri)
        product_predictions = neural_predictions
    except requests.exceptions.HTTPError as e:
        resp = e.response
        logger.error(
            f"Category classifier returned an error: {resp.status_code}: %s", resp.text
        )
        return

    if len(product_predictions) < 1:
        return

    for prediction in product_predictions:
        prediction.barcode = product_id.barcode
        prediction.server_type = product_id.server_type

    import_result = import_insights(product_predictions, product_id.server_type)
    logger.info(import_result)


def updated_product_predict_insights(
    product_id: ProductIdentifier, product: JSONType
) -> None:
    """Predict and import category insights and insights-derived from product
    name.

    :param product_id: identifier of the product
    :param product: product as retrieved from MongoDB
    """
    add_category_insight(product_id, product)
    product_name = product.get("product_name")

    if not product_name:
        return

    if product_id.server_type.is_food():
        # Only available for food products for now
        logger.info("Generating predictions from product name...")
        predictions_all = get_predictions_from_product_name(product_id, product_name)
        import_result = import_insights(predictions_all, product_id.server_type)
        logger.info(import_result)
