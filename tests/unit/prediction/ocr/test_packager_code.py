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
        ("Conditionné par EMB 72264", ["EMB 72264"]),
        ("EMB 56251E", ["EMB 56251E"]),
        ("emb 56 251 e", ["EMB 56251E"]),
        ("EMB 562511", []),
        # Corsican communes have an INSEE code starting with 2A or 2B
        ("EMB 2A004", ["EMB 2A004"]),
        ("emb 2b033c", ["EMB 2B033C"]),
        ("EMB 2C004", []),
        ("FR 2A.004.009 CE", ["FR 2A.004.009 EC"]),
        ("FR 56.251.001 CE", ["FR 56.251.001 EC"]),
        ("DE BY-12345 EG", ["DE BY-12345 EC"]),
        ("FSC C012345", ["FSC-C012345"]),
        # ("EST  \n 31778", ["EST. 31778"]),
        # ("EST  \n 9999", []),
        # ("M31779+  P31779+  \tV31779", ["M31779", "P31779", "V31779"]),
    ],
)
def test_find_packager_codes(text: str, values: list[str]):
    insights = find_packager_codes(text)
    detected_values = set(i.value for i in insights)
    assert detected_values == set(values)
