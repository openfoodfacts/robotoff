import typing

from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import ProductInsights, RawInsight
from robotoff.utils.types import JSONType

from .xgfood import XGFood


def get_xgfood_categories_as_insights(product: JSONType):
    """Predict category using the XGFood categorizer.

    XGFood is a XGBoost algorithm trained to predict categories on two levels
    (PNNS 1 and PNNS 2) using the product name and the list of parsed ingredients.
    """
    # Get product data
    product_name = product.get("product_name_fr", "")
    ingredients = product.get("ingredients", [])

    # Run predictions
    result = XGFood().predict(product_name=product_name, ingredients=ingredients)

    # Parse predictions as Insights
    insights = [
        _get_xgfood_raw_insight(
            result["prediction_G1"], result["confidence_G1"], "group_1"
        ),
        _get_xgfood_raw_insight(
            result["prediction_G2"], result["confidence_G2"], "group_2"
        ),
    ]

    # Return as ProductInsights bundle
    return ProductInsights(
        barcode=product["code"],
        type=InsightType.category,
        insights=[insight for insight in insights if insight is not None],
    )


def _get_xgfood_raw_insight(
    prediction: str, confidence: float, level: str
) -> typing.Optional[RawInsight]:
    if prediction != "unknown":
        return RawInsight(
            type=InsightType.category,
            value_tag=prediction,
            data={"model": "xgfood", "level": "group_2", "confidence": confidence},
            predictor="xgfood",
        )
    return None
