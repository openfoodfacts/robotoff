from typing import Dict, List

import pytest

from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.ml.category.neural.category_classifier import (
    CategoryClassifier,
    Prediction,
)
from robotoff.taxonomy import Taxonomy


def test_prediction_to_raw_insight():
    prediction = Prediction("category", 0.9)

    assert prediction.to_raw_insight() == RawInsight(
        type=InsightType.category,
        value_tag="category",
        data={"lang": "xx", "model": "neural", "confidence": 0.9},
    )


class MockResponse:
    def __init__(self, prediction: Dict):
        self.prediction = prediction

    def raise_for_status(self):
        pass

    def json(self) -> Dict:
        return self.prediction


def _prediction_resp(categories: List[str], confs: List[float]) -> MockResponse:
    return MockResponse(
        prediction={
            "predictions": [
                {"output_mapper_layer": confs, "output_mapper_layer_1": categories},
            ]
        }
    )


@pytest.mark.parametrize(
    "deepest_only,mock_response,want_predictions",
    [
        # Nothing predicted - nothing returned.
        (False, _prediction_resp([], []), None),
        # Low prediction confidences - nothing returned.
        (False, _prediction_resp(["en:meat", "en:fish"], [0.3, 0.3]), None),
        # Only the high confidence prediction is returned.
        (
            False,
            _prediction_resp(["en:fish", "en:meat"], [0.7, 0.3]),
            [Prediction("en:fish", 0.7)],
        ),
        # Only the leaves of the taxonomy are returned.
        (
            True,
            _prediction_resp(["en:fish", "en:smoked-salmon"], [0.8, 0.8]),
            [Prediction("en:smoked-salmon", 0.8)],
        ),
    ],
)
def test_predict(mocker, deepest_only, mock_response, want_predictions):
    category_taxonomy = Taxonomy.from_dict(
        {
            "en:meat": {
                "names": "meat",
            },
            "en:fish": {
                "names": "fish",
            },
            "en:salmon": {
                "names": "salmon",
                "parents": ["en:fish"],
            },
            "en:smoked-salmon": {
                "names": "salmon",
                "parents": ["en:salmon"],
            },
        }
    )

    classifier = CategoryClassifier(category_taxonomy)

    mocker.patch(
        "robotoff.ml.category.neural.category_classifier.http_session.post",
        return_value=mock_response,
    )

    predictions = classifier.predict(
        {"ingredients_tags": ["ingredient1"], "product_name": "Test Product"},
        deepest_only,
    )

    assert predictions == want_predictions
