import logging

import pytest

from robotoff.prediction.ocr.core import extract_predictions
from robotoff.prediction.types import PredictionType


def test_extract_predictions_category_deactivated(caplog):
    """Category OCR prediction is deactivated for now"""
    caplog.set_level(logging.INFO)
    result = extract_predictions("spam", PredictionType.category)
    assert result == []
    (logged,) = caplog.records
    assert logged.msg.startswith("Skipping category OCR prediction")


def test_extract_predictions_unknown_raises():
    """If we extract an unknown insights it raises"""
    with pytest.raises(ValueError, match="unknown prediction type"):
        extract_predictions("spam", PredictionType.ingredient_spellcheck)
