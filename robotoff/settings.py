from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / 'ml' / 'data'
CATEGORIES_PATH = DATA_DIR / 'categories.min.json'
DATASET_PATH = DATA_DIR / 'en.openfoodfacts.org.products.csv'
