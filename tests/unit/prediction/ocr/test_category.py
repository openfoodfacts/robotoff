import pytest
from pytest_mock import MockerFixture

from robotoff.prediction.ocr.category import find_category
from robotoff.taxonomy import Taxonomy


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("Appellation Clairette de Die Controlée", ["fr:clairette-de-die"]),
        ("Appellation Clairette de Die Protégée", ["fr:clairette-de-die"]),
        ("Appellation    Clairette \tde Die\n Protégée", ["fr:clairette-de-die"]),
        ("Chinon appellation d'origine protégée", ["fr:chinon"]),
        ("Appellation Chinon Contrôlée", ["fr:chinon"]),
        ("Appellation Côtes du Rhône Contrôlée", ["fr:cotes-du-rhone"]),
        ("APPELLATION CÔTES DU RHÔNE CONTRÔLÉE", ["fr:cotes-du-rhone"]),
        ("Appellation Saint-Émilion Contrôlée", ["fr:saint-emilion"]),
        (
            "Châteauneuf-du-Pape appellation d'origine protégée",
            ["fr:chateauneuf-du-pape"],
        ),
        (
            "Denominacion de Origen ProtegidA PIMENTON de la VERA",
            ["es:pimenton-de-la-vera"],
        ),
        ("DOP Mozzarella    di bufala campana", ["en:mozzarella-di-bufala-campana"]),
        ("Mixed puffed cereals    AOP", ["en:mixed-puffed-cereals"]),
    ],
)
def test_find_category_from_AOC(
    text: str,
    value_tags: list[str],
    category_taxonomy: Taxonomy,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "robotoff.prediction.ocr.category.get_taxonomy", return_value=category_taxonomy
    )
    insights = find_category(text)
    detected_value_tags = set(i.value_tag for i in insights)
    assert detected_value_tags == set(value_tags)
