from typing import Dict, Set

import pytest

from robotoff import settings
from robotoff.prediction.ocr.brand import (
    extract_brands,
    generate_brand_keyword_processor,
)
from robotoff.utils import text_file_iter


def test_check_logo_annotation_brands():
    items: Set[str] = set()

    for item in text_file_iter(settings.OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH):
        assert "||" in item
        assert item not in items
        items.add(item)


@pytest.fixture(scope="session")
def brand_taxonomy_keyword_processor():
    yield generate_brand_keyword_processor(
        text_file_iter(settings.OCR_TAXONOMY_BRANDS_PATH)
    )


@pytest.fixture(scope="session")
def brand_keyword_processor():
    yield generate_brand_keyword_processor(text_file_iter(settings.OCR_BRANDS_PATH))


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Le comptoir de Mathilde bon vous propose",
            {
                "value": "Le Comptoir de Mathilde",
                "value_tag": "le-comptoir-de-mathilde",
                "predictor": "test",
                "data": {"text": "Le comptoir de Mathilde", "notify": False},
                "automatic_processing": False,
            },
        ),
        ("Netto gewitch: 450 g", None),
        ("", None),
        (
            "Notre marque Alpina savoie est bien positionnée",
            {
                "value": "Alpina Savoie",
                "value_tag": "alpina-savoie",
                "predictor": "test",
                "data": {"text": "Alpina savoie", "notify": False},
                "automatic_processing": False,
            },
        ),
    ],
)
def test_extract_brand_taxonomy(
    brand_taxonomy_keyword_processor, text: str, expected: Dict
):
    insights = extract_brands(
        brand_taxonomy_keyword_processor, text, "test", automatic_processing=False
    )

    if not expected:
        assert not insights
    else:
        insight = insights[0]
        for expected_key, expected_value in expected.items():
            assert getattr(insight, expected_key) == expected_value


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "le nouveau cocacola",
            {
                "value": "Coca-Cola",
                "value_tag": "coca-cola",
                "predictor": "test",
                "data": {"text": "cocacola", "notify": False},
                "automatic_processing": True,
            },
        ),
    ],
)
def test_extract_brand(brand_keyword_processor, text: str, expected):
    insights = extract_brands(
        brand_keyword_processor, text, "test", automatic_processing=True
    )

    if not expected:
        assert not insights
    else:
        insight = insights[0]
        for expected_key, expected_value in expected.items():
            assert getattr(insight, expected_key) == expected_value
