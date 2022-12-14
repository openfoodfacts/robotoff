import requests

from robotoff.insights.extraction import get_predictions_from_product_name
from robotoff.insights.importer import import_insights, refresh_insights
from robotoff.models import with_db
from robotoff.off import ServerType, get_server_type
from robotoff.prediction.category.matcher import predict as predict_category_matcher
from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.products import get_product
from robotoff.redis import Lock, LockedResourceException
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


@with_db
def update_insights_job(barcode: str, server_domain: str):
    """This job is triggered by the webhook API, when product information has
    been updated.

    When a product is updated, Robotoff will:

    1. Generate new predictions related to the product's category and name.
    2. Regenerate all insights from the product associated predictions.
    """
    logger.info("Running `update_insights` for product %s (%s)", barcode, server_domain)

    try:
        with Lock(
            name=f"robotoff:product_update_job:{barcode}", expire=300, timeout=10
        ):
            # We handle concurrency thanks to the lock as the task will fetch
            # product from MongoDB at the time it runs, it's not worth
            # reprocessing with another task arriving concurrently.
            # The expire is there only in case the lock is not released
            # (process killed)
            product_dict = get_product(barcode)

            if product_dict is None:
                logger.warning("Updated product does not exist: %s", barcode)
                return

            updated_product_predict_insights(barcode, product_dict, server_domain)
            logger.info("Refreshing insights...")
            imported = refresh_insights(barcode, server_domain)
            logger.info("%s insights created after refresh", imported)
    except LockedResourceException:
        logger.info(
            f"Couldn't acquire product_update lock, skipping product_update for product {barcode}"
        )


def add_category_insight(barcode: str, product: JSONType, server_domain: str) -> bool:
    """Predict categories for product and import predicted category insight.

    :param barcode: product barcode
    :param product: product as retrieved from application
    :param server_domain: the server the product belongs to
    :return: True if at least one category insight was imported
    """
    if get_server_type(server_domain) != ServerType.off:
        return False

    logger.info("Predicting product categories...")
    # predict category using matching algorithm on product name
    product_predictions = predict_category_matcher(product)

    # predict category using neural model
    try:
        product_predictions += CategoryClassifier(
            get_taxonomy(TaxonomyType.category.name)
        ).predict(product)
    except requests.exceptions.HTTPError as e:
        resp = e.response
        logger.error(
            f"Category classifier returned an error: {resp.status_code}: %s", resp.text
        )

    if len(product_predictions) < 1:
        return False

    for prediction in product_predictions:
        prediction.barcode = barcode

    imported = import_insights(product_predictions, server_domain)
    logger.info("%s category insight imported for product %s", imported, barcode)

    return bool(imported)


def updated_product_predict_insights(
    barcode: str, product: JSONType, server_domain: str
) -> bool:
    updated = add_category_insight(barcode, product, server_domain)
    product_name = product.get("product_name")

    if not product_name:
        return updated

    logger.info("Generating predictions from product name...")
    predictions_all = get_predictions_from_product_name(barcode, product_name)
    imported = import_insights(predictions_all, server_domain)
    logger.info("%s insights imported for product %s", imported, barcode)

    if imported:
        updated = True

    return updated
