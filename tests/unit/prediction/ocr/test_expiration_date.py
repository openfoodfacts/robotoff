import pytest

from robotoff.prediction.ocr.expiration_date import find_expiration_date


@pytest.mark.parametrize(
    "text,expected_values",
    [
        ("mindestens haltbar bis 06.07.19", ["2019-07-06"]),
        ("a consommer avant le 03/09/2024", ["2024-09-03"]),
        ("best before 03/09/2024", ["2024-09-03"]),
        ("03/09/2024", ["2024-09-03"]),
        ("32/01/2024", []),
    ],
)
def test_find_expiration_date_parsing(text: str, expected_values: list[str]):
    predictions = find_expiration_date(text)
    assert [prediction.value for prediction in predictions] == expected_values


def test_find_expiration_date_ignores_ambiguous_slash_format_for_german_text():
    text = "mindestens haltbar bis 06/07/2019"

    assert find_expiration_date(text) == []
