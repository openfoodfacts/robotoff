from typing import List

import pytest

from robotoff.prediction.ocr.packager_code import find_packager_codes


@pytest.mark.parametrize(
    "text,values",
    [
        ("Sustainable palm oil RSPO-5068502 ", ["RSPO-5068502"]),
        ("RSPO-50685022", []),
        ("QRSPO-2404885", []),
        ("FR-012-345", ["FR-012-345"]),
        ("FR-AB0-123", []),
        ("fr-098-123", []),
        ("Gluten code is FR-234-234 ", ["FR-234-234"]),
        # ("EST  \n 31778", ["EST. 31778"]),
        # ("EST  \n 9999", []),
        # ("M31779+  P31779+  \tV31779", ["M31779", "P31779", "V31779"]),
    ],
)
def test_find_packager_codes(text: str, values: List[str]):
    insights = find_packager_codes(text)
    detected_values = set(i.value for i in insights)
    assert detected_values == set(values)
