from typing import Tuple

import pytest

from robotoff.insights.ocr.dataclass import OCRRegex
from robotoff.insights.ocr.product_weight import (PRODUCT_WEIGHT_REGEX,
                                                  normalize_weight,
                                                  is_valid_weight,
                                                  is_extreme_weight,
                                                  is_suspicious_weight)


@pytest.mark.parametrize('input_str,is_match', [
    ("poids net à l'emballage: 500g", True),
    ("poids 2kg", True),
    ("poids 2kgv", False),
    ("qpoids 2kgv", False),
    ("net wt. 1.4 fl oz", True),
    ("other string", False),
    ("1.4 g", False),
    ("2 l", False),
])
def test_product_weight_with_mention_regex(input_str: str, is_match: bool):
    with_mention_ocr_regex: OCRRegex = PRODUCT_WEIGHT_REGEX['with_mention']
    with_mention_regex = with_mention_ocr_regex.regex

    assert (with_mention_regex.match(input_str) is not None) == is_match


@pytest.mark.parametrize('input_str,is_match', [
    ("poids net à l'emballage: 500g", False),
    ("poids 2kg", False),
    ("250g net weight", True),
    ("10 g net", True),
    ("bq10 g net", False),
    ("1.4 g", False),
    ("2 l", False),
])
def test_product_weight_with_ending_mention_regex(input_str: str, is_match: bool):
    ocr_regex: OCRRegex = PRODUCT_WEIGHT_REGEX['with_ending_mention']
    regex = ocr_regex.regex

    assert (regex.match(input_str) is not None) == is_match


@pytest.mark.parametrize('value,unit,expected', [
    ("2", "l", (2000., 'ml')),
    ("1549.45", "dl", (154945., 'ml')),
    ("10,5", "cl", (105, 'ml')),
    ("20", "ml", (20., 'ml')),
    ("2,5", "kg", (2500., 'g')),
    ("2.5", "g", (2.5, 'g')),
    ("25", "g", (25, 'g')),
    ("15", "fl oz", (450, 'ml')),
    ("1", "oz", (28.349523125, 'g')),
])
def test_normalize_weight(value: str, unit: str,
                          expected: Tuple[float, str]):
    result = normalize_weight(value, unit)
    assert result == expected


@pytest.mark.parametrize('value,is_valid', [
    ("25", True),
    ("150", True),
    ("150.0", True),
    ("0225", False),
    ("00225", False),
    ("gsg", False),
    ("-15", False),
    ("12,5", False),
    ("12.5", False),
])
def test_is_valid_weight(value: str, is_valid: bool):
    assert is_valid_weight(value) is is_valid


@pytest.mark.parametrize('value,unit,expected', [
    (10000, 'g', True),
    (10000, 'ml', True),
    (9999, 'ml', False),
    (9999, 'g', False),
    (100, 'g', False),
    (100, 'ml', False),
    (10, 'ml', True),
    (3, 'ml', True),
    (10, 'g', True),
    (2, 'g', True),
])
def test_is_extreme_weight(value: float, unit: str, expected: bool):
    assert is_extreme_weight(value, unit) is expected


@pytest.mark.parametrize('value,unit,expected', [
    (100, 'g', False),
    (125, 'g', False),
    (250, 'g', False),
    (100, 'ml', False),
    (563, 'ml', False),
    (2530, 'g', False),
    (6250, 'ml', False),
    (2532, 'g', True),
    (2537, 'ml', True),
    (6259, 'ml', True),
])
def test_is_suspicious_weight(value: float, unit: str, expected: bool):
    assert is_suspicious_weight(value, unit) is expected
