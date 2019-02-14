from pathlib import Path
import os

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / 'data'
DATASET_DIR = PROJECT_DIR / 'datasets'
CATEGORIES_PATH = DATA_DIR / 'categories.json'
DATASET_PATH = DATASET_DIR / 'en.openfoodfacts.org.products.csv'
JSONL_DATASET_PATH = DATASET_DIR / 'products.jsonl.gz'
JSONL_DATASET_ETAG_PATH = DATASET_DIR / 'products-etag.txt'
JSONL_MIN_DATASET_PATH = DATASET_DIR / 'products-min.jsonl.gz'
JSONL_DATASET_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"

DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")

IPC_AUTHKEY = os.environ.get("IPC_AUTHKEY", "IPC").encode('utf-8')
IPC_HOST = os.environ.get("IPC_HOST", "localhost")
IPC_PORT = os.environ.get("IPC_PORT", 6650)
IPC_ADDRESS = (IPC_HOST, IPC_PORT)
WORKER_COUNT = os.environ.get("WORKER_COUNT", 4)

ELASTICSEARCH_HOSTS = os.environ.get("ELASTICSEARCH_HOSTS", "localhost:9200").split(",")
ELASTICSEARCH_TYPE = "document"

ELASTICSEARCH_CATEGORY_INDEX = 'category'
ELASTICSEARCH_PRODUCT_INDEX = 'product'
