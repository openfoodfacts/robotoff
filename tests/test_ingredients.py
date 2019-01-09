from robotoff.ingredients import process_ingredients, normalize_ingredients, Ingredients


def test_normalize_ingredients():
    text = "farine de blé 10,5%, huile de colza 8%, soja 0,15%"
    normalized = normalize_ingredients(text)
    assert normalized == "farine de blé      , huile de colza   , soja      "


def test_process_ingredients():
    text = "Eau, oeufs frais, farine de blé 19%, huile de colza, lactose et protéines de lait, sel, extrait d'épices"
    normalized = "Eau  oeufs frais  farine de blé      huile de colza  lactose et protéines de lait  sel  " \
                 "extrait d'épices"
    ingredients = process_ingredients(text)
    assert isinstance(ingredients, Ingredients)
    assert ingredients.text == text
    assert ingredients.normalized == normalized
    assert ingredients.offsets == [(0, 3), (4, 16), (17, 35), (36, 51), (52, 81), (82, 86), (87, 104)]
