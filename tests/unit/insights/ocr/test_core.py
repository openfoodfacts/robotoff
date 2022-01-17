import logging

import pytest

from robotoff.insights import InsightType
from robotoff.prediction.ocr.core import extract_predictions


def test_extract_predictions_category_deactivated(caplog):
    """Category OCR prediction is deactivated for now"""
    caplog.set_level(logging.INFO)
    result = extract_predictions("spam", InsightType.category)
    assert result == []
    (logged,) = caplog.records
    assert logged.msg.startswith("Skipping category OCR prediction")


def test_extract_predictions_unknown_raises():
    """If we extract an unknown insights it raises"""
    with pytest.raises(ValueError, match="unknown insight type"):
        extract_predictions("spam", InsightType.ingredient_spellcheck)
