import re
from typing import Set

import pytest

from robotoff import settings
from robotoff.insights.ocr.brand import BRAND_REGEX, generate_brand_keyword_processor, \
    extract_brands_taxonomy
from robotoff.taxonomy import Taxonomy
from robotoff.utils import text_file_iter


@pytest.mark.parametrize('input_str,is_match', [
    ("other string", False),
    ("carre", False),
    ("carrefour", True),
    ("monoprix p'tit prix", True),
    ("marks & spencer", True),
    ("nestlé", True),
    ("nestle", True),
    ("carrefour gaby", True),
    ("carrefour baby", True),
    ("dr. oetker", True),
    ("dr oetker", True),
    ("m-budget", True),
    ("la belle iloise", True),
    ("la belle-îloise", True),
])
def test_brand_regex(input_str: str, is_match: bool):
    regex = BRAND_REGEX.regex
    assert (regex.match(input_str) is not None) == is_match


def test_check_ocr_brands():
    brands: Set[str] = set()
    items: Set[str] = set()

    for item in text_file_iter(settings.OCR_BRANDS_DATA_PATH):
        assert item not in items
        items.add(item)

        assert '’' not in item
        if '||' in item:
            brand, regex_str = item.split('||')
        else:
            brand = item
            regex_str = re.escape(item.lower())

        assert brand not in brands
        re.compile(regex_str)

        brands.add(brand)

    items = set()
    for item in text_file_iter(settings.OCR_BRANDS_NOTIFY_DATA_PATH):
        assert item in brands
        assert item not in items
        items.add(item)


def test_check_logo_annotation_brands():
    items: Set[str] = set()

    for item in text_file_iter(settings.OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH):
        assert '||' in item
        assert item not in items
        items.add(item)


@pytest.fixture(scope='session')
def brand_keyword_processor():
    yield generate_brand_keyword_processor(min_length=6)


@pytest.mark.parametrize("text,expected", [
    ("Le comptoir de Mathilde bon vous propose", {'brand': "Le Comptoir de Mathilde", "brand_tag": "le-comptoir-de-mathilde", "text": "Le comptoir de Mathilde"}),
    ("Netto gewitch: 450 g", None),
    ("", None),
    ("Notre marque Alpina savoie est bien positionnée", {'brand': "Alpina Savoie", "brand_tag": "alpina-savoie", "text": "Alpina savoie"}),
])
def test_extract_brand_taxonomy(brand_keyword_processor, text: str, expected):
    insights = extract_brands_taxonomy(brand_keyword_processor, text)

    if not expected:
        assert not insights
    else:
        insight = insights[0]
        for expected_key, expected_value in expected.items():
            assert expected_key in insight
            assert insight[expected_key] == expected_value
