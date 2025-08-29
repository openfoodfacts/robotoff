import math

import pytest

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
