import pytest

from robotoff.utils.text import get_tag


@pytest.mark.parametrize(
    "value,output",
    [
        ("Reflets de France", "reflets-de-france"),
        ("écrasé", "ecrase"),
        ("Søstrene Grene", "sostrene-grene"),
        ("søstrene-grene", "sostrene-grene"),
        ("Nøgne Ø", "nogne-o"),
        ("nøgne-ø", "nogne-o"),
        ("œufs de plein air", "oeufs-de-plein-air"),
        ("dr.oetker", "dr-oetker"),
        ("mat & lou", "mat-lou"),
        ("monop'daily", "monop-daily"),
        ("épi d'or", "epi-d-or"),
        ("Health Star Rating 0.5", "health-star-rating-0-5"),
        ("C'est qui le Patron ?!", "c-est-qui-le-patron"),
        # Cyrillic characters should be kept
        ("люкс", "люкс"),
    ],
)
def test_get_tag(value: str, output: str):
    assert get_tag(value) == output
