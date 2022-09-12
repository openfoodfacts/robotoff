from typing import List

import pytest

from robotoff.prediction.ocr.category_from_AOC import find_category_from_AOC


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("Appellation Clairette de Die Controlée", ["fr:clairette-de-die"]),
        ("Appellation Clairette de Die Protégée", ["fr:clairette-de-die"]),
        ("Appellation    Clairette \tde Die\n Protégée", ["fr:clairette-de-die"]),
        ("Chinon appellation d'origine protégée", ["fr:chinon"]),
        ("Denominacion de Origen ProtegidA PIMENTON de la VERA", ["es:pimenton-de-la-vera"]),
        ("DOP Mozzarella    di bufala campana", ["en:mozzarella-di-bufala-campana"]),
        ("Mixed puffed cereals    AOP", ["en:mixed-puffed-cereals"]),
    ],
)
def test_find_category_from_AOC(text: str, value_tags: List[str]):
    insights = find_category_from_AOC(text)
    detected_value_tags = set(i.value_tag for i in insights)
    assert detected_value_tags == set(value_tags)
