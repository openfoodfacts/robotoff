from typing import List, Optional

import pytest

from robotoff.prediction.ocr.label import LABELS_REGEX, find_labels

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


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("certifié ab.", ["en:ab-agriculture-biologique"]),
        ("décret du 5/01/07", ["en:label-rouge"]),
        ("DECRET du 05.01.07", ["en:label-rouge"]),
        ("Homologation n° LA 21/88", ["en:label-rouge"]),
        ("homologation LA 42/05", ["en:label-rouge"]),
        ("Homologation n°LA19/05", ["en:label-rouge"]),
        ("Homologation n°LA 02/91", ["en:label-rouge"]),
    ],
)
def test_find_labels(text: str, value_tags: List[str]):
    insights = find_labels(text)
    detected_value_tags = set(i.value_tag for i in insights)
    assert detected_value_tags == set(value_tags)
