import logging

import requests

from robotoff.insights.importer import import_insights
from robotoff.models import with_db
from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.products import get_product
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.types import JSONType, Prediction, ProductIdentifier
from robotoff.workers.queues import enqueue_job, get_high_queue

logger = logging.getLogger(__name__)


@with_db
def add_category_insight_job(
    product_id: ProductIdentifier, triton_uri: str | None = None
) -> None:
    """Job to add category insight for a product.

    :param product_id: identifier of the product
    :param triton_uri: URI of the Triton Inference Server, defaults to
        None. If not provided, the default value from settings is used.
    """
    product_dict = get_product(product_id)

    if product_dict is None:
        logger.info("Product does not exist: %s", product_id)
        return

    add_category_insight(
        product_id, product_dict, triton_uri=triton_uri, async_import=True
    )


def add_category_insight(
    product_id: ProductIdentifier,
    product: JSONType,
    triton_uri: str | None = None,
    async_import: bool = False,
) -> None:
    """Predict categories for product and import predicted category insight.

    :param product_id: identifier of the product
    :param product: product as retrieved from MongoDB
    :param triton_uri: URI of the Triton Inference Server, defaults to
        None. If not provided, the default value from settings is used.
    :param async_import: whether to import insights asynchronously using rq, in a
        product-specific rq queue, defaults to False
    """
    if not product_id.server_type.is_food():
        # Category prediction is only available for Food products
        logger.info(
            "`server_type=%s`, skipping category prediction", product_id.server_type
        )
        return

    if product.get("schema_version", 999) > 1002:
        # Don't predict category if we use the new schema version
        # This is temporary, before we roll out the new schema support
        return

    logger.info("Launching category prediction for %s", product_id)
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

    if async_import:
        enqueue_job(
            import_category_predictions_job,
            get_high_queue(product_id),
            job_kwargs={"result_ttl": 0},
            product_id=product_id,
            predictions=product_predictions,
        )
    else:
        for prediction in product_predictions:
            prediction.barcode = product_id.barcode
            prediction.server_type = product_id.server_type

        import_result = import_insights(product_predictions, product_id.server_type)
        logger.info(import_result)


@with_db
def import_category_predictions_job(
    product_id: ProductIdentifier, predictions: list[Prediction]
) -> None:
    """Import category predictions as insights.

    :param predictions: list of category predictions
    """
    for prediction in predictions:
        prediction.barcode = product_id.barcode
        prediction.server_type = product_id.server_type

    import_result = import_insights(predictions, product_id.server_type)
    logger.info(import_result)
