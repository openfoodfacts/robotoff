from robotoff.utils.text import get_tag

import pytest


@pytest.mark.parametrize(
    "value,output",
    [
        ("Reflets de France", "reflets-de-france"),
        ("écrasé", "ecrase"),
        ("œufs de plein air", "oeufs-de-plein-air"),
        ("dr.oetker", "dr-oetker"),
        ("mat & lou", "mat-lou"),
        ("monop'daily", "monop-daily"),
        ("épi d'or", "epi-d-or"),
        ("Health Star Rating 0.5", "health-star-rating-0-5"),
    ],
)
def test_get_tag(value: str, output: str):
    assert get_tag(value) == output
