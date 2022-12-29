import pytest

from robotoff.logos import compute_iou, generate_prediction
from robotoff.prediction.types import Prediction
from robotoff.types import PredictionType


@pytest.mark.parametrize(
    "box_1,box_2,expected_iou",
    [
        ((0.0, 0.0, 0.1, 0.1), (0.2, 0.2, 0.4, 0.4), 0.0),
        ((0.1, 0.1, 0.5, 0.5), (0.1, 0.1, 0.5, 0.5), 1.0),
        ((0.1, 0.1, 0.5, 0.5), (0.2, 0.2, 0.6, 0.6), (0.3 * 0.3) / (0.16 * 2 - 0.09)),
        ((0.2, 0.2, 0.6, 0.6), (0.1, 0.1, 0.5, 0.5), (0.3 * 0.3) / (0.16 * 2 - 0.09)),
    ],
)
def test_compute_iou(box_1, box_2, expected_iou):
    assert compute_iou(box_1, box_2) == expected_iou


@pytest.mark.parametrize(
    "logo_type,logo_value,data,automatic_processing,confidence,prediction",
    [
        ("category", "en:breads", {}, False, None),
        ("label", None, {}, False, None),
        (
            "label",
            "en:eu-organic",
            {},
            False,
            0.8,
            Prediction(
                type=PredictionType.label,
                data={},
                value_tag="en:eu-organic",
                value=None,
                automatic_processing=False,
                predictor="universal-logo-detector",
                confidence=0.5,
            ),
        ),
        (
            "brand",
            "carrefour",
            {},
            False,
            0.5,
            Prediction(
                type=PredictionType.brand,
                data={},
                value_tag="carrefour",
                value="carrefour",
                automatic_processing=False,
                predictor="universal-logo-detector",
                confidence=0.5,
            ),
        ),
    ],
)
def test_generate_prediction(
    logo_type, logo_value, data, automatic_processing, confidence, prediction
):
    assert (
        generate_prediction(
            logo_type, logo_value, data, confidence, automatic_processing
        )
        == prediction
    )
