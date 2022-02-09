from typing import Set

import pytest

from robotoff import settings
from robotoff.prediction.ocr.packaging import find_packaging
from robotoff.utils import text_file_iter


def test_packaging_format():
    patterns = set()
    items = list(text_file_iter(settings.OCR_PACKAGING_DATA_PATH))
    for item in items:
        assert "||" in item, f"missing || separator for item {item}"
        splitted = item.split("||")
        assert len(splitted) == 2, f"key||pattern format expected, here: {item}"
        pattern = splitted[1]
        pattern = pattern.lower()
        assert pattern not in patterns, f"duplicated pattern: {pattern}"
        patterns.add(pattern)


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("Tetrapack", {"tetra-pack"}),
        ("tetrapack", {"tetra-pack"}),
        ("Packaging: boîte en carton,...", {"fr:boite-en-carton"}),
        ("Ingrédients: 100% tomate", set()),
    ],
)
def test_find_packaging(text: str, value_tags: Set[str]):
    insights = find_packaging(text)
    detected_values = set(i.value_tag for i in insights)
    assert detected_values == value_tags
