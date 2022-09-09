from typing import List, Optional

import pytest

from robotoff.prediction.ocr.category_from_AOC import AOC_REGEX, find_category_from_AOC


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("Appellation Clairette de Die Controlée", ["fr:clairette-de-die"]),
        ("Appellation Clairette de Die Protégée", ["fr:clairette-de-die"]),
        ("Chinon appellation d'origine protégée", ["fr:chinon"]),
    ],
)
def test_find_category_from_AOC(text: str, value_tags: List[str]):
    insights = find_category_from_AOC(text)
    detected_value_tags = set(i.value_tag for i in insights)
    assert detected_value_tags == set(value_tags)
