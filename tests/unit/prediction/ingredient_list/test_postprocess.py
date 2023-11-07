import pytest

from robotoff.prediction.ingredient_list.postprocess import (
    ORGANIC_MENTIONS_RE,
    detect_additional_mentions,
)


@pytest.mark.parametrize(
    "text,match",
    [
        ("Ingrédients issus de l'agriculture biologique", True),
        ("*Ingrédients agricoles issus de l'agriculture biologique", True),
        ("*issu de l'agriculture biologique", True),
        ("issu de l'agriculture biologique", True),
        ("*Produits issus de l'agriculture biologique", True),
        ("Produit issu de l'agriculture biologique", True),
        ("\"produit issu de l'agriculture durable", True),
        ("*= produits issus de l'agriculture biologique", True),
        ("* = ingrédients issus de l'agriculture durable", True),
        ("* Produit issu de l'Agriculture Biologique", True),
        ("*organic", True),
        ("organic", False),
        ("agriculture biologique", False),
        ("produit issu", False),
    ],
)
def test_organic_mention_detection(text: str, match: bool):
    assert (ORGANIC_MENTIONS_RE.match(text) is not None) is match


@pytest.mark.parametrize(
    "text, initial_end_idx, new_end_idx",
    [
        (", *ingrédients issus de l'agriculture biologique", 0, 48),
        (
            "Eau, poireaux*, carottes*, navet*. *= produits issus de l'agriculture durable. Valeurs nutritionnelles",
            33,
            77,
        ),
        (
            "Eau, poireaux*, carottes*, navet*, *ingrédients issus de l'agriculture bio. Valeurs nutritionnelles",
            33,
            74,
        ),
        # If no mention was detected, reset the end index to its initial value
        (
            "Eau, poireaux*, carottes*, navet*, ",
            33,
            33,
        ),
    ],
)
def test_detect_additional_mentions(text: str, initial_end_idx, new_end_idx: int):
    assert detect_additional_mentions(text, initial_end_idx) == new_end_idx
