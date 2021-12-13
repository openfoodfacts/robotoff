import logging

import pytest

from robotoff.insights import InsightType
from robotoff.insights.ocr.core import extract_insights


def test_extract_insights_category_deactivated(caplog):
    """Category OCR prediction is deactivated for now"""
    caplog.set_level(logging.INFO)
    result = extract_insights("spam", InsightType.category)
    assert result == []
    (logged,) = caplog.records
    assert logged.msg.startswith("Skipping category OCR prediction")


def test_extract_insights_unknown_raises():
    """If we extract an unknown insights it raises"""
    with pytest.raises(ValueError, match="unknown insight type"):
        extract_insights("spam", InsightType.ingredient_spellcheck)
