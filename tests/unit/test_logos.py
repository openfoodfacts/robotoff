import pytest

from robotoff.logos import generate_prediction
from robotoff.prediction.types import Prediction, PredictionType


@pytest.mark.parametrize(
    "logo_type,logo_value,data,automatic_processing,prediction",
    [
        ("category", "en:breads", {}, False, None),
        ("label", None, {}, False, None),
        (
            "label",
            "en:eu-organic",
            {},
            False,
            Prediction(
                type=PredictionType.label,
                data={},
                value_tag="en:eu-organic",
                value=None,
                automatic_processing=False,
                predictor="universal-logo-detector",
            ),
        ),
        (
            "brand",
            "carrefour",
            {},
            False,
            Prediction(
                type=PredictionType.brand,
                data={},
                value_tag="carrefour",
                value="carrefour",
                automatic_processing=False,
                predictor="universal-logo-detector",
            ),
        ),
    ],
)
def test_generate_prediction(
    logo_type, logo_value, data, automatic_processing, prediction
):
    assert (
        generate_prediction(logo_type, logo_value, data, automatic_processing)
        == prediction
    )
