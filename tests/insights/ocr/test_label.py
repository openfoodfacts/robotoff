from typing import Optional

import pytest

from robotoff.insights.ocr.label import LABELS_REGEX

XX_BIO_XX_OCR_REGEX = LABELS_REGEX["xx-bio-xx"][0]
ES_BIO_OCR_REGEX = LABELS_REGEX["xx-bio-xx"][1]


@pytest.mark.parametrize(
    "input_str,is_match,output",
    [
        ("ES-ECO-001-AN", True, "en:es-eco-001-an"),
        ("ES-ECO-001", False, None),
        ("ES-ECO-001-", False, None),
        ("FR-BIO-01", False, None),
    ],
)
def test_es_ocr_regex(input_str: str, is_match: bool, output: Optional[str]):
    regex = ES_BIO_OCR_REGEX.regex
    match = regex.match(input_str)
    assert (match is not None) == is_match

    if is_match:
        assert ES_BIO_OCR_REGEX.processing_func(match) == output  # type: ignore
