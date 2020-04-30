import pytest

from robotoff.ingredients import process_ingredients, normalize_ingredients, Ingredients


@pytest.mark.parametrize(
    "text,normalized",
    [
        (
            "farine de blé 10,5%, huile de colza 8%, soja 0,15%",
            "farine de blé      , huile de colza   , soja      ",
        ),
        (
            "Eau, céréales 15,2 % (épeautre 7 %, riz 6 %, °avoine_), pâte",
            "Eau, céréales        (épeautre    , riz    , °avoine ), pâte",
        ),
        (
            "Eau, céréales 15.2% (E162, E 262i, E1905iii), 151",
            "Eau, céréales       (    ,       ,         ),    ",
        ),
        ("EPAUTRE 100 %", "EPAUTRE      "),  # Test spurious E XXX additive detection
        ("0ignons (35%)", "0ignons (   )"),
        ("2-methylcellulose", "2-methylcellulose"),
        (
            "_lait_ entier, _crème_ (_lait_), protéines de _lait_",
            " lait  entier,  crème  ( lait ), protéines de  lait ",
        ),
    ],
)
def test_normalize_ingredients(text, normalized):
    assert normalized == normalize_ingredients(text)


def test_process_ingredients():
    text = "Eau, oeufs frais, farine de blé 19%, huile de colza, lactose et protéines de lait, sel, extrait d'épices"
    normalized = (
        "Eau  oeufs frais  farine de blé      huile de colza  lactose et protéines de lait  sel  "
        "extrait d'épices"
    )
    ingredients = process_ingredients(text)
    assert isinstance(ingredients, Ingredients)
    assert ingredients.text == text
    assert ingredients.normalized == normalized
    assert ingredients.offsets == [
        (0, 3),
        (4, 16),
        (17, 35),
        (36, 51),
        (52, 81),
        (82, 86),
        (87, 104),
    ]
