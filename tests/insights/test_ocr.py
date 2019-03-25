import pytest
from robotoff.insights.ocr import PRODUCT_WEIGHT_REGEX, OCRRegex


@pytest.mark.parametrize('input_str,is_match', [
    ("poids net à l'emballage: 500g", True),
    ("poids 2kg", True),
    ("poids 2kgv", False),
    ("net wt. 1.4 fl oz", True),
    ("other string", False),
    ("1.4 g", False),
    ("2 l", False),
])
def test_product_weight_with_mention_regex(input_str: str, is_match: bool):
    with_mention_ocr_regex: OCRRegex = PRODUCT_WEIGHT_REGEX['with_mention']
    with_mention_regex = with_mention_ocr_regex.regex

    assert (with_mention_regex.match(input_str) is not None) == is_match
