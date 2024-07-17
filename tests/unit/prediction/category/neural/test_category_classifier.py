import numpy as np
import pytest

from robotoff.prediction.category.neural.category_classifier import CategoryClassifier
from robotoff.triton import serialize_byte_tensor
from robotoff.types import ProductIdentifier, ServerType

MODEL_VERSION = "category-classifier"
DEFAULT_PRODUCT_ID = ProductIdentifier("123", ServerType.off)


class GRPCResponse:
    def __init__(self, labels: list[str], scores: list[float]):
        self.raw_output_contents = [
            np.array(scores, dtype=np.float32).tobytes(),
            serialize_byte_tensor(np.array(labels, dtype=np.object_)),
        ]


class MockStub:
    def __init__(self, response):
        self.response = response

    def ModelInfer(self, request):
        return self.response


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
def test_predict_ingredients_only(mocker, data, category_taxonomy):
    mocker.patch(
        "robotoff.prediction.category.neural.category_classifier.get_triton_inference_stub",
        return_value=MockStub(GRPCResponse(["en:meats"], [0.99])),
    )
    classifier = CategoryClassifier(category_taxonomy)
    predictions, debug = classifier.predict(data, DEFAULT_PRODUCT_ID)
    assert debug == {
        "inputs": {
            "ingredients_tags": [""],
            "product_name": data["product_name"],
            "carbohydrates": -1,
            "energy_kcal": -1,
            "fat": -1,
            "saturated_fat": -1,
            "fiber": -1,
            "fruits_vegetables_nuts": -1,
            "proteins": -1,
            "salt": -1,
            "sugars": -1,
            "ingredients_ocr_tags": [""],
            "num_images": 0,
        },
        "model_name": "keras-image-embeddings-3.0",
        "threshold": 0.5,
    }
    assert len(predictions) == 1
    prediction = predictions[0]
    assert prediction.value_tag == "en:meats"
    assert np.isclose(prediction.confidence, 0.99)


@pytest.mark.parametrize(
    "deepest_only,mock_response,expected_values",
    [
        # Nothing predicted - nothing returned.
        (False, GRPCResponse([], []), []),
        # Low prediction confidences - nothing returned.
        (False, GRPCResponse(["en:meats", "en:fishes"], [0.3, 0.3]), []),
        # Only the high confidence prediction is returned.
        (
            False,
            GRPCResponse(["en:fishes", "en:meats"], [0.7, 0.3]),
            [("en:fishes", 0.7)],
        ),
        # Only the leaves of the taxonomy are returned.
        (
            True,
            GRPCResponse(["en:fishes", "en:smoked-salmons"], [0.8, 0.8]),
            [("en:smoked-salmons", 0.8)],
        ),
    ],
)
def test_predict(
    mocker, deepest_only, mock_response, expected_values, category_taxonomy
):
    classifier = CategoryClassifier(category_taxonomy)
    mocker.patch(
        "robotoff.prediction.category.neural.category_classifier.get_triton_inference_stub",
        return_value=MockStub(mock_response),
    )
    predictions, _ = classifier.predict(
        {"ingredients_tags": ["ingredient1"], "product_name": "Test Product"},
        DEFAULT_PRODUCT_ID,
        deepest_only,
    )

    assert len(predictions) == len(expected_values)

    for prediction, (value_tag, confidence) in zip(predictions, expected_values):
        assert prediction.value_tag == value_tag
        assert np.isclose(prediction.confidence, confidence)
