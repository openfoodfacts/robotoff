from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.ml.category.neural.category_classifier import Prediction


def test_prediction_to_raw_insight():
    prediction = Prediction("category", 0.9)

    assert prediction.to_raw_insight() == RawInsight(
        type=InsightType.category,
        value_tag="category",
        data={"lang": "xx", "model": "neural", "confidence": 0.9},
    )
