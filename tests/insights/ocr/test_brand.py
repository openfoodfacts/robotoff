import re
from typing import Set

import pytest

from robotoff import settings
from robotoff.insights.ocr.brand import BRAND_REGEX
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
