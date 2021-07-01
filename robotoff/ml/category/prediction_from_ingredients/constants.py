import json
from pathlib import Path

import numpy as np

with (Path(__file__).parent / "features.json").open() as f:
    FEATURES = json.load(f)

# TODO: move all weights file paths definition in the same place.
# Model can be downloaded from the CLI.
MODEL_G1_URL = "https://github.com/openfoodfacts/robotoff-models/releases/download/category-predictor-xgfood-emlyon-1.0/xgfood_model_g1.model"  # noqa: E501
MODEL_G1_FILEPATH = Path("weights/xgfood_model_g1.model")

MODEL_G2_URL = "https://github.com/openfoodfacts/robotoff-models/releases/download/category-predictor-xgfood-emlyon-1.0/xgfood_model_g2.model"  # noqa: E501
MODEL_G2_FILEPATH = Path("weights/xgfood_model_g2.model")

LABELS_G1 = [
    "beverages",
    "cereals and potatoes",
    "composite foods",
    "fat and sauces",
    "fish meat eggs",
    "fruits and vegetables",
    "milk and dairy products",
    "salty snacks",
    "sugary snacks",
    "unknown",
]

LABELS_G2 = [
    "appetizers",
    "artificially sweetened beverages",
    "biscuits and cakes",
    "bread",
    "breakfast cereals",
    "cereals",
    "cheese",
    "chocolate products",
    "dairy desserts",
    "dressings and sauces",
    "dried fruits",
    "eggs",
    "fats",
    "fish and seafood",
    "fruit juices",
    "fruit nectars",
    "fruits",
    "ice cream",
    "legumes",
    "meat",
    "milk and yogurt",
    "nuts",
    "offals",
    "one dish meals",
    "pastries",
    "pizza pies and quiche",
    "plant based milk substitutes",
    "potatoes",
    "processed meat",
    "salty and fatty products",
    "sandwiches",
    "soups",
    "sweetened beverages",
    "sweets",
    "teas and herbal teas and coffees",
    "unsweetened beverages",
    "vegetables",
    "waters and flavored waters",
    "unknown",
]

_THRESHOLDS_G1 = {
    "beverages": 0.6,
    "cereals and potatoes": 0.5,
    "composite foods": 0.5,
    "fat and sauces": 0.6,
    "fish meat eggs": 0.5,
    "fruits and vegetables": 0.5,
    "milk and dairy products": 0.5,
    "salty snacks": 0.5,
    "sugary snacks": 0.5,
}

_THRESHOLDS_G2 = {
    "appetizers": 0.75,
    "artificially sweetened beverages": 0.65,
    "biscuits and cakes": 0.75,
    "bread": 0.75,
    "breakfast cereals": 0.75,
    "cereals": 0.75,
    "cheese": 0.8,
    "chocolate products": 0.55,
    "dairy desserts": 0.55,
    "dressings and sauces": 0.85,
    "dried fruits": 0.65,
    "eggs": 0.65,
    "fats": 0.75,
    "fish and seafood": 0.75,
    "fruit juices": 0.65,
    "fruit nectars": 0.7,
    "fruits": 0.65,
    "ice cream": 0.75,
    "legumes": 0.65,
    "meat": 0.75,
    "milk and yogurt": 0.75,
    "nuts": 0.75,
    "offals": 0.55,
    "one dish meals": 0.88,
    "pastries": 0.65,
    "pizza pies and quiche": 0.55,
    "plant based milk substitutes": 0.65,
    "potatoes": 0.7,
    "processed meat": 0.75,
    "salty and fatty products": 0.75,
    "sandwiches": 0.65,
    "soups": 0.7,
    "sweetened beverages": 0.7,
    "sweets": 0.6,
    "teas and herbal teas and coffees": 0.8,
    "unsweetened beverages": 0.8,
    "vegetables": 0.5,
    "waters and flavored waters": 0.6,
}

THRESHOLDS_G1_AS_NP = np.array(
    [_THRESHOLDS_G1[label] for label in LABELS_G1 if label != "unknown"]
)
THRESHOLDS_G2_AS_NP = np.array(
    [_THRESHOLDS_G2[label] for label in LABELS_G2 if label != "unknown"]
)
