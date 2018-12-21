from pathlib import Path
import os

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / 'data'
CATEGORIES_PATH = DATA_DIR / 'categories.min.json'
DATASET_PATH = DATA_DIR / 'en.openfoodfacts.org.products.csv'
JSONL_DATASET_PATH = DATA_DIR / 'products.jsonl.gz'

DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")
