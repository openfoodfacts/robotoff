from typing import Dict, Set

import pytest

from robotoff import settings
from robotoff.insights.ocr.brand import (
    generate_brand_keyword_processor,
    extract_brands,
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
                "data": {"text": "Le comptoir de Mathilde", "data_source": "test"},
            },
        ),
        ("Netto gewitch: 450 g", None),
        ("", None),
        (
            "Notre marque Alpina savoie est bien positionnée",
            {
                "value": "Alpina Savoie",
                "value_tag": "alpina-savoie",
                "data": {"text": "Alpina savoie", "data_source": "test"},
            },
        ),
    ],
)
def test_extract_brand_taxonomy(
    brand_taxonomy_keyword_processor, text: str, expected: Dict
):
    insights = extract_brands(brand_taxonomy_keyword_processor, text, "test")

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
                "data": {"text": "cocacola", "data_source": "test"},
            },
        ),
    ],
)
def test_extract_brand(brand_keyword_processor, text: str, expected):
    insights = extract_brands(brand_keyword_processor, text, "test")

    if not expected:
        assert not insights
    else:
        insight = insights[0]
        for expected_key, expected_value in expected.items():
            assert getattr(insight, expected_key) == expected_value
