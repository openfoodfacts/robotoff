import pytest

from robotoff.insights import InsightType
from robotoff.prediction.ocr.core import extract_predictions


def test_extract_insights_unknown_raises():
    """If we extract an unknown insights it raises"""
    with pytest.raises(ValueError, match="unknown prediction type"):
        extract_predictions("spam", InsightType.ingredient_spellcheck)
