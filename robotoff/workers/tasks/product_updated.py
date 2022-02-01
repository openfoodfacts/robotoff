import time

import requests

from robotoff import settings
from robotoff.elasticsearch.category.predict import (
    predict_from_product as predict_category_from_product_es,
)
from robotoff.insights.extraction import get_predictions_from_product_name
from robotoff.insights.importer import import_insights, refresh_insights
from robotoff.off import ServerType, get_server_type
from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.prediction.types import PredictionType, ProductPredictions
from robotoff.products import get_product
from robotoff.taxonomy import TaxonomyType, get_taxonomy
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def update_insights(barcode: str, server_domain: str):
    # Sleep 10s to let the OFF update request that triggered the webhook call
    # to finish
    time.sleep(settings.UPDATED_PRODUCT_WAIT)
    product_dict = get_product(barcode)

    if product_dict is None:
        logger.warn("Updated product does not exist: {}".format(barcode))
        return

    updated = updated_product_predict_insights(barcode, product_dict, server_domain)

    if updated:
        logger.info("Product {} updated".format(barcode))

    refresh_insights(barcode, server_domain, automatic=True)


def add_category_insight(barcode: str, product: JSONType, server_domain: str) -> bool:
    """Predict categories for product and import predicted category insight.

    :param barcode: product barcode
    :param product: product as retrieved from application
    :param server_domain: the server the product belongs to
    :return: True if at least one category insight was imported
    """
    if get_server_type(server_domain) != ServerType.off:
        return False

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
        product_insight = ProductPredictions(
            barcode=product["code"],
            type=PredictionType.category,
            predictions=[
                category_prediction.to_prediction()
                for category_prediction in category_predictions
            ],
        )
        product_predictions.append(product_insight)

    if len(product_predictions) < 1:
        return False

    merged_product_prediction = ProductPredictions.merge(product_predictions)
    imported = import_insights(
        [merged_product_prediction], server_domain, automatic=True
    )

    if imported:
        logger.info("Category insight imported for product {}".format(barcode))

    return bool(imported)


def updated_product_predict_insights(
    barcode: str, product: JSONType, server_domain: str
) -> bool:
    updated = add_category_insight(barcode, product, server_domain)
    product_name = product.get("product_name")

    if not product_name:
        return updated

    predictions_all = get_predictions_from_product_name(barcode, product_name)
    imported = import_insights(
        list(predictions_all.values()), server_domain, automatic=False
    )
    if imported:
        logger.info("{} insights imported for product {}".format(imported, barcode))
        updated = True

    return updated
