import json
from pathlib import Path

import pytest

from robotoff.ml.category.prediction_from_ingredients.xgfood import (
    XGFood,
    XGFoodPrediction,
)

EXAMPLES_DIRPATH = Path(__file__).parent / "examples"


@pytest.mark.parametrize(
    ("example_id", "expected_result"),
    [
        (
            # https://fr.openfoodfacts.org/produit/3228857000852/pain-100-mie-nature-pt-harrys
            "3228857000852",
            {
                "prediction_G1": "cereals and potatoes",
                "confidence_G1": 0.9791,
                "prediction_G2": "bread",
                "confidence_G2": 0.99212,
            },
        ),
        (
            # https://fr.openfoodfacts.org/produit/3366321052331/st-hubert-bio-doux-pour-tartine-et-cuisine
            "3366321052331",
            {
                "prediction_G1": "salty snacks",
                "confidence_G1": 0.65916,
                "prediction_G2": "salty and fatty products",
                "confidence_G2": 0.86683,
            },
        ),
        (
            # https://fr.openfoodfacts.org/produit/3088543506255/sirop-d-agave-sunny-via
            "3088543506255",
            {
                "prediction_G1": "beverages",
                "confidence_G1": 0.81433,
                "prediction_G2": "unknown",
                "confidence_G2": 0.0,
            },
        ),
        (
            # https://fr.openfoodfacts.org/produit/3225350000501/pulco-citron
            "3225350000501",
            {
                "prediction_G1": "beverages",
                "confidence_G1": 0.78247,
                "prediction_G2": "unknown",
                "confidence_G2": 0.0,
            },
        ),
        (
            # https://fr.openfoodfacts.org/produit/3523230028431/buche-sainte-maure-soignon
            "3523230028431",
            {
                "prediction_G1": "milk and dairy products",
                "confidence_G1": 0.99738,
                "prediction_G2": "cheese",
                "confidence_G2": 0.99257,
            },
        ),
    ],
)
def test_xgfood(example_id: str, expected_result: XGFoodPrediction) -> None:
    """Test XGFood model works as expected.

    See ./robotoff/ml/category/prediction_from_ingredients/xgfood.py for
    more details.
    """
    filepath = EXAMPLES_DIRPATH / (example_id + ".json")
    assert filepath.is_file()

    with filepath.open() as f:
        data = json.load(f)

    product_name = data["product"].get("product_name_fr", "")
    ingredients = data["product"].get("ingredients", [])

    result = XGFood().predict(product_name=product_name, ingredients=ingredients)
    assert result == expected_result
