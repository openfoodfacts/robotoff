import datetime
import operator
from typing import Dict, Iterable, Optional

from robotoff.elasticsearch.category.match import predict_category
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
from robotoff.products import ProductDataset
from robotoff.utils import get_logger
from robotoff.utils.es import get_es_client

logger = get_logger(__name__)


def predict(client, product: Dict) -> Optional[ProductPredictions]:
    """Predict product categories using ES

    :param elasticsearch.Elasticsearch client: connection to ES instance
    :param product: product properties

    :return: an ProductPrediction on category or None if no prediction was available
    """
    predictions = []

    for lang in product.get("languages_codes", []):
        product_name = product.get("product_name_{}".format(lang))

        if not product_name:
            continue

        prediction = predict_category(client, product_name, lang)

        if prediction is None:
            continue

        category, score = prediction
        predictions.append((lang, category, product_name, score))
        continue

    if predictions:
        # Sort by descending score
        sorted_predictions = sorted(
            predictions, key=operator.itemgetter(2), reverse=True
        )

        p = sorted_predictions[0]
        lang, category, product_name, score = p

        return ProductPredictions(
            barcode=product["code"],
            type=PredictionType.category,
            predictions=[
                Prediction(
                    type=PredictionType.category,
                    value_tag=category,
                    data={
                        "lang": lang,
                        "product_name": product_name,
                        "model": "matcher",
                    },
                )
            ],
        )

    return None


def predict_from_product(product: Dict) -> Optional[ProductPredictions]:
    client = get_es_client()
    return predict(client, product)


def predict_from_iterable(
    client, products: Iterable[Dict]
) -> Iterable[ProductPredictions]:
    """Iterative version of :py:func:`predict`"""
    for product in products:
        prediction = predict(client, product)

        if prediction:
            yield prediction


def predict_from_dataset(
    dataset: ProductDataset, from_datetime: Optional[datetime.datetime] = None
) -> Iterable[ProductPredictions]:
    """Return an iterable of category predictions, using the provided dataset.

    Args:
        dataset: a ProductDataset
        from_datetime: datetime threshold: only keep products modified after
            `from_datetime`
    """
    product_stream = (
        dataset.stream()
        .filter_nonempty_text_field("code")
        .filter_nonempty_text_field("product_name")
        .filter_empty_tag_field("categories_tags")
        .filter_nonempty_tag_field("countries_tags")
        .filter_nonempty_tag_field("languages_codes")
    )

    if from_datetime:
        product_stream = product_stream.filter_by_modified_datetime(
            from_t=from_datetime
        )

    product_iter = product_stream.iter()
    logger.info("Performing prediction on products without categories")

    es_client = get_es_client()
    yield from predict_from_iterable(es_client, product_iter)
