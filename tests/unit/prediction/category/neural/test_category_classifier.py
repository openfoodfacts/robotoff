from typing import Dict, List

import pytest

from robotoff.insights.dataclass import InsightType
from robotoff.prediction.category.neural.category_classifier import (
    CategoryClassifier,
    CategoryPrediction,
)
from robotoff.prediction.types import Prediction
from robotoff.taxonomy import Taxonomy


def test_category_prediction_to_prediction():
    category_prediction = CategoryPrediction("category", 0.9)

    assert category_prediction.to_prediction() == Prediction(
        type=InsightType.category,
        value_tag="category",
        data={"lang": "xx", "model": "neural", "confidence": 0.9},
        automatic_processing=True,
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


def test_predict_missing_data():
    classifier = CategoryClassifier(None)

    predicted = classifier.predict(
        {"WRONG_ingredients_tags": ["ingredient1"]},
    )

    assert not predicted


@pytest.mark.parametrize(
    "data",
    [
        # missing ingredients_tags
        {"product_name": "Test Product"},
        # ingredients_tag empty
        {
            "ingredients_tags": [],
            "product_name": "Test Product",
        },
    ],
    ids=[
        "missing ingredients_tags",
        "ingredients_tag empty",
    ],
)
def test_predict_ingredients_only(mocker, data):
    mocker.patch(
        "robotoff.prediction.category.neural.category_classifier.http_session.post",
        return_value=_prediction_resp(["en:meat"], [0.99]),
    )
    classifier = CategoryClassifier({"en:meat": {"names": "meat"}})
    predictions = classifier.predict(data)
    assert predictions == [CategoryPrediction("en:meat", 0.99)]


@pytest.mark.parametrize(
    "data",
    [
        {"ingredients_tags": ["ingredient1"]},  # missing product_name
        {"ingredients_tags": ["ingredient1"], "product_name": ""},  # product_name empty
    ],
    ids=[
        "missing product_name",
        "product_name empty",
    ],
)
def test_predict_product_no_title(mocker, data):
    mocker.patch(
        "robotoff.prediction.category.neural.category_classifier.http_session.post",
        return_value=_prediction_resp(["en:meat"], [0.99]),
    )
    classifier = CategoryClassifier({"en:meat": {"names": "meat"}})
    predictions = classifier.predict(data)
    assert predictions is None


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
            [CategoryPrediction("en:fish", 0.7)],
        ),
        # Only the leaves of the taxonomy are returned.
        (
            True,
            _prediction_resp(["en:fish", "en:smoked-salmon"], [0.8, 0.8]),
            [CategoryPrediction("en:smoked-salmon", 0.8)],
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
        "robotoff.prediction.category.neural.category_classifier.http_session.post",
        return_value=mock_response,
    )

    predictions = classifier.predict(
        {"ingredients_tags": ["ingredient1"], "product_name": "Test Product"},
        deepest_only,
    )

    assert predictions == want_predictions
