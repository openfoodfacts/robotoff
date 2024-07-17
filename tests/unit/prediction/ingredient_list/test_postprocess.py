import pytest

from robotoff.prediction.ingredient_list.postprocess import (
    ORGANIC_MENTIONS_RE,
    detect_additional_mentions,
    detect_trace_mention,
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
        ('"aus biologischer Landwirtschaft', True),
        ("*de cultivo ecologico certificado", True),
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
        (
            "Eau, poireaux*, carottes*, navet*, *ingrédients issus de l'agriculture bio. Peut contenir des traces de noix. Valeurs nutritionnelles",
            33,
            108,
        ),
        (
            "Eau, poireaux*, carottes*, navet*. Peut contenir des traces de noix. *ingrédients issus de l'agriculture bio. Valeurs nutritionnelles",
            33,
            108,
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


@pytest.mark.parametrize(
    "text, new_end_idx",
    [
        ("Peut contenir des traces de fruit à coque.", 41),
        (
            "Peut contenir des traces de soja, lait, sésame, amande, noisette, noix de cajou et arachide !",
            91,
        ),
        ("Eau, banane", 0),
        ("peut contenir des traces d'arachides et de cacahuètes. Attention", 53),
        (
            "produit élaboré dans un atelier utilisant du lait demi-écrémé et du gorgonzola. OTHER",
            78,
        ),
        # This should not match, as the string does not start with the
        # allergen mention
        ("OTHER. Peut contenir des traces d'arachides et de cacahuètes", 0),
        ("contient naturellement du jaune d'oeuf. Info nutritionnelles", 38),
        # This should not match, as the first word is "acontient" and not
        # "contient" (we check for word boundaries)
        ("acontient naturellement du jaune d'oeuf. Info nutritionnelles", 0),
        # EN
        ("contains wheat", 14),
    ],
)
def test_detect_trace_mention(text: str, new_end_idx: int):
    assert detect_trace_mention(text, end_idx=0) == new_end_idx


@pytest.mark.parametrize(
    "text",
    [
        # FR
        "Peut contenir des traces de fruit à coque",
        # ES
        "CONTIENE LECHE",
        "Contiene lecitina de soya",
        "Este producto contiene espelta, trigo y gluten",
        "PUEDE CONTENER LECHE",
    ],
)
def test_detect_trace_mention_full_match(text: str):
    """Test that the trace mention detection works (only full matches are
    tested here)."""
    assert detect_trace_mention(text, end_idx=0) == len(text)
