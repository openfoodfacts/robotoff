from typing import Set

import pytest

from robotoff import settings
from robotoff.prediction.ocr.packaging import find_packaging
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.utils import text_file_iter


def test_packaging_format():
    patterns = set()
    items = list(text_file_iter(settings.OCR_PACKAGING_DATA_PATH))
    for item in items:
        assert "||" in item, f"missing || separator for item {item}"
        splitted = item.split("||")
        assert len(splitted) == 2, f"key||pattern format expected, here: {item}"
        key, pattern = splitted
        assert not any(
            x.startswith(" ") or x.endswith(" ") for x in key.split(";")
        ), f"space after ';' separator: {item}"
        pattern = pattern.lower()
        assert pattern not in patterns, f"duplicated pattern: {pattern}"
        patterns.add(pattern)


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("Tetrapack", {"tetra-pack"}),
        ("tetrapack", {"tetra-pack"}),
        ("Packaging: boîte carton,...", {"fr:boite-en-carton"}),
        ("Ingrédients: 100% tomate", set()),
        ("", set()),
        (
            "emballage: bouteille verre et son bouchon...",
            {"fr:bouteille-en-verre", "fr:bouchon"},
        ),
    ],
)
def test_find_packaging(text: str, value_tags: Set[str]):
    predictions = find_packaging(text)
    detected_values = set(i.value_tag for i in predictions)
    assert detected_values == value_tags

    for prediction in predictions:
        assert isinstance(prediction, Prediction)
        assert prediction.type is PredictionType.packaging
