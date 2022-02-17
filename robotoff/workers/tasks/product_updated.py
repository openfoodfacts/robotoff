import time

import requests

from robotoff import settings
from robotoff.elasticsearch.category.predict import (
    predict_from_product as predict_category_from_product_es,
)
from robotoff.insights.extraction import get_predictions_from_product_name
from robotoff.insights.importer import import_insights, refresh_insights
from robotoff.models import with_db
from robotoff.off import ServerType, get_server_type
from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.prediction.types import PredictionType, ProductPredictions
from robotoff.products import get_product
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


@with_db
def update_insights(barcode: str, server_domain: str):
    # Sleep 10s to let the OFF update request that triggered the webhook call
    # to finish
    logger.info(f"Running `update_insights` for product {barcode} ({server_domain})")

    time.sleep(settings.UPDATED_PRODUCT_WAIT)
    product_dict = get_product(barcode)

    if product_dict is None:
        logger.warning(f"Updated product does not exist: {barcode}")
        return

    updated_product_predict_insights(barcode, product_dict, server_domain)
    logger.info("Refreshing insights...")
    imported = refresh_insights(barcode, server_domain, automatic=True)
    logger.info(f"{imported} insights created after refresh")


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
    # predict category using Elasticsearch on title
    product_predictions = []
    product_insight = predict_category_from_product_es(product)

    if product_insight is not None:
        product_predictions.append(product_insight)

    # predict category using neural model
    category_predictions = None
    try:
        category_predictions = CategoryClassifier(
            get_taxonomy(TaxonomyType.category.name)
        ).predict(product)
    except requests.exceptions.HTTPError as e:
        resp = e.response
        logger.error(
            f"Category classifier returned an error: {resp.status_code}: {resp.text}"
        )

    if category_predictions is not None:
        product_predictions.append(
            ProductPredictions(
                barcode=barcode,
                type=PredictionType.category,
                predictions=[
                    category_prediction.to_prediction()
                    for category_prediction in category_predictions
                ],
            )
        )

    if len(product_predictions) < 1:
        return False

    merged_product_prediction = ProductPredictions.merge(product_predictions)
    imported = import_insights(
        [merged_product_prediction], server_domain, automatic=True
    )
    logger.info(f"{imported} category insight imported for product {barcode}")

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
    imported = import_insights(
        list(predictions_all.values()), server_domain, automatic=False
    )
    logger.info(f"{imported} insights imported for product {barcode}")

    if imported:
        updated = True

    return updated
