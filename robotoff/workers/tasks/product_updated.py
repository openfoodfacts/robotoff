import time
from typing import Dict, Optional

import requests

from robotoff import settings
from robotoff.elasticsearch.category.predict import (
    predict_from_product as predict_category_from_product_es,
)
from robotoff.insights.dataclass import InsightType
from robotoff.insights.extraction import get_predictions_from_product_name
from robotoff.insights.importer import InsightImporterFactory
from robotoff.insights.validator import (
    InsightValidationResult,
    InsightValidator,
    InsightValidatorFactory,
    validate_insight,
)
from robotoff.models import ProductInsight
from robotoff.off import ServerType, get_server_type
from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.prediction.types import PredictionType, ProductPredictions
from robotoff.products import Product, get_product, get_product_store
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

    update_ingredients(barcode, product_dict, server_domain)

    product = Product(product_dict)
    validators: Dict[str, Optional[InsightValidator]] = {}

    for insight in (
        ProductInsight.select()
        .where(
            ProductInsight.annotation.is_null(),
            ProductInsight.barcode == barcode,
            ProductInsight.server_domain == server_domain,
        )
        .iterator()
    ):
        if insight.type not in validators:
            validators[insight.type] = InsightValidatorFactory.create(
                insight.type, None
            )

        validator = validators[insight.type]

        if validator is not None:
            result = validate_insight(insight, validator=validator, product=product)
            if result == InsightValidationResult.deleted:
                logger.info(
                    "Insight {} deleted (type: {})".format(insight.id, insight.type)
                )
            elif result == InsightValidationResult.updated:
                logger.info(
                    "Insight {} converted to latent (type: {})".format(
                        insight.id, insight.type
                    )
                )


def add_category_insight(barcode: str, product: JSONType, server_domain: str) -> bool:
    if get_server_type(server_domain) != ServerType.off:
        return False

    product_predictions = []
    product_insight = predict_category_from_product_es(product)

    if product_insight is not None:
        product_predictions.append(product_insight)

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
    product_store = get_product_store()
    importer = InsightImporterFactory.create(InsightType.category, product_store)

    imported = importer.import_insights(
        [merged_product_prediction],
        server_domain=server_domain,
        automatic=False,
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

    product_store = get_product_store()
    predictions_all = get_predictions_from_product_name(barcode, product_name)

    for prediction_type, predictions in predictions_all.items():
        importer = InsightImporterFactory.create(
            InsightType[prediction_type], product_store
        )
        imported = importer.import_insights(
            [predictions], server_domain=server_domain, automatic=False
        )

        if imported:
            logger.info(
                "{} insights ({}) imported for product {}".format(
                    imported, prediction_type, barcode
                )
            )
            updated = True

    return updated


def update_ingredients(barcode: str, product: JSONType, server_domain: str) -> int:
    deleted = 0

    for insight in ProductInsight.select().where(
        ProductInsight.type == InsightType.ingredient_spellcheck.name,
        ProductInsight.annotation.is_null(True),
        ProductInsight.barcode == barcode,
    ):
        lang = insight.data["lang"]
        insight_text = insight.data["text"]
        field_name = "ingredients_text_{}".format(lang)

        if field_name not in product or product[field_name] != insight_text:
            logger.info(
                "Ingredients deleted or updated for product {} (lang: {}), deleting "
                "insight".format(barcode, lang)
            )
            insight.delete_instance()
            deleted += 1

    return deleted
