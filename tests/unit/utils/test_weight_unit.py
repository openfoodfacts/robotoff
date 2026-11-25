import math
from collections.abc import Callable

import pytest

from robotoff.prediction.ocr.product_weight import (
    normalize_weight as normalize_product_weight,
)
from robotoff.utils.weight_unit import normalize_weight


@pytest.mark.parametrize(
    "value,unit,expected",
    [
        ("2", "l", (2000.0, "ml")),
        ("1549.45", "dl", (154945.0, "ml")),
        ("10,5", "cl", (105, "ml")),
        ("20", "ml", (20.0, "ml")),
        ("2,5", "kg", (2500.0, "g")),
        ("2.5", "g", (2.5, "g")),
        ("25", "g", (25, "g")),
        ("15", "fl oz", (450, "ml")),
        ("1", "oz", (28.349523125, "g")),
    ],
)
def test_normalize_weight(value: str, unit: str, expected: tuple[float, str]):
    normalized_value, normalized_unit = normalize_weight(value, unit)
    assert math.isclose(normalized_value, expected[0])
    assert normalized_unit == expected[1]


def test_normalize_weight_invalid_unit():
    with pytest.raises(ValueError, match="unknown unit: meter / second"):
        normalize_weight("100", "m/s")


@pytest.mark.parametrize(
    "normalizer",
    [normalize_weight, normalize_product_weight],
    ids=["shared", "ocr"],
)
@pytest.mark.parametrize(
    "value,unit,expected",
    [
        ("1.001", "kg", (1001, "g")),
        ("1,001", "kg", (1001, "g")),
        ("1.001", "l", (1001, "ml")),
        ("1.1", "cl", (11, "ml")),
        ("250", "g", (250, "g")),
        ("0", "ml", (0, "ml")),
    ],
)
def test_normalize_weight_removes_rounding_noise(
    normalizer: Callable[[str, str], tuple[float, str]],
    value: str,
    unit: str,
    expected: tuple[float, str],
):
    # Exact equality catches noise that an isclose assertion would hide.
    assert normalizer(value, unit) == expected


@pytest.mark.parametrize(
    "normalizer",
    [normalize_weight, normalize_product_weight],
    ids=["shared", "ocr"],
)
@pytest.mark.parametrize(
    "value,unit,expected",
    [
        ("2.5", "g", (2.5, "g")),
        ("2.75", "ml", (2.75, "ml")),
        ("0.0015", "kg", (1.5, "g")),
        ("0.0025", "l", (2.5, "ml")),
    ],
)
def test_normalize_weight_preserves_fractional_quantities(
    normalizer: Callable[[str, str], tuple[float, str]],
    value: str,
    unit: str,
    expected: tuple[float, str],
):
    assert normalizer(value, unit) == expected
