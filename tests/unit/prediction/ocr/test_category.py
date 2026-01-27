import pytest

from robotoff.prediction.ocr.category import find_category


@pytest.mark.parametrize(
    "text,value_tags",
    [
        ("Appellation Clairette de Die Controlée", ["fr:clairette-de-die"]),
        ("Appellation Clairette de Die Protégée", ["fr:clairette-de-die"]),
        ("Appellation    Clairette \tde Die\n Protégée", ["fr:clairette-de-die"]),
        ("Chinon appellation d'origine protégée", ["fr:chinon"]),
        (
            "Denominacion de Origen ProtegidA PIMENTON de la VERA",
            ["es:pimenton-de-la-vera"],
        ),
        ("DOP Mozzarella    di bufala campana", ["en:mozzarella-di-bufala-campana"]),
        ("Mixed puffed cereals    AOP", ["en:mixed-puffed-cereals"]),
    ],
)
def test_find_category_from_AOC(text: str, value_tags: list[str]):
    insights = find_category(text)
    detected_value_tags = set(i.value_tag for i in insights)
    assert detected_value_tags == set(value_tags)


def test_category_taxonomisation(mocker):
    from robotoff.prediction.ocr.category import category_taxonomisation

    # Mock match_taxonomized_value
    mock_match = mocker.patch("robotoff.prediction.ocr.category.match_taxonomized_value")
    mock_match.return_value = "en:mocked-category"

    # Mock simple regex match object
    mock_re_match = mocker.Mock()
    mock_re_match.group.return_value = " Some Category "

    # Test execution
    result = category_taxonomisation("en:", mock_re_match)

    # Verify normalization and args
    # Expected: "en:" + normalize_tag(" Some Category ") -> "en:some-category"
    mock_match.assert_called_once_with("en:some-category", "category")
    assert result == "en:mocked-category"
