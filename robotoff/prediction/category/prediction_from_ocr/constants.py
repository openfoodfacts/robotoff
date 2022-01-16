from pathlib import Path

# TODO: move all weights file paths definition in the same place.
# Model an be downloaded from the CLI.
RIDGE_PREDICTOR_URL = "https://github.com/openfoodfacts/robotoff-models/releases/download/category-predictor-ocr-lewagon-1.0/bestridge_compressed.joblib"
RIDGE_PREDICTOR_FILEPATH = Path("models/weights/bestridge_compressed.joblib")

LIST_CATEGORIES = [
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
]
