from pathlib import Path
import os
from typing import Tuple

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATASET_DIR = PROJECT_DIR / "datasets"
DATASET_DIR.mkdir(exist_ok=True)
I18N_DIR = PROJECT_DIR / "i18n"
DATASET_PATH = DATASET_DIR / "en.openfoodfacts.org.products.csv"
JSONL_DATASET_PATH = DATASET_DIR / "products.jsonl.gz"
JSONL_DATASET_ETAG_PATH = DATASET_DIR / "products-etag.txt"
JSONL_MIN_DATASET_PATH = DATASET_DIR / "products-min.jsonl.gz"
DATASET_CHECK_MIN_PRODUCT_COUNT = 1000000
INSIGHT_DUMP_PATH = DATASET_DIR / "insights.jsonl.gz"

JSONL_DATASET_URL = (
    "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
)

TAXONOMY_CATEGORY_URL = (
    "https://static.openfoodfacts.org/data/taxonomies/categories.full.json"
)
TAXONOMY_INGREDIENT_URL = (
    "https://static.openfoodfacts.org/data/taxonomies/ingredients.full.json"
)
TAXONOMY_LABEL_URL = "https://static.openfoodfacts.org/data/taxonomies/labels.full.json"
TAXONOMY_BRAND_URL = "https://static.openfoodfacts.org/data/taxonomies/brands.full.json"
OFF_IMAGE_BASE_URL = "https://static.openfoodfacts.org/images/products"
OFF_BASE_WEBSITE_URL = "https://world.openfoodfacts.org"
OFF_BRANDS_URL = OFF_BASE_WEBSITE_URL + "/brands.json"

OFF_PASSWORD = os.environ.get("OFF_PASSWORD", "")
OFF_SERVER_DOMAIN = "api.openfoodfacts.org"

TAXONOMY_DIR = DATA_DIR / "taxonomies"
TAXONOMY_CATEGORY_PATH = TAXONOMY_DIR / "categories.full.json"
TAXONOMY_INGREDIENT_PATH = TAXONOMY_DIR / "ingredients.full.json"
TAXONOMY_LABEL_PATH = TAXONOMY_DIR / "labels.full.json"
TAXONOMY_BRAND_PATH = TAXONOMY_DIR / "brands.full.json"
INGREDIENTS_FR_PATH = TAXONOMY_DIR / "ingredients_fr.txt"
INGREDIENT_TOKENS_PATH = TAXONOMY_DIR / "ingredients_tokens.txt"
FR_TOKENS_PATH = TAXONOMY_DIR / "fr_tokens_lower.gz"

DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")

MONGO_URI = "mongodb://localhost:27017"

IPC_AUTHKEY = os.environ.get("IPC_AUTHKEY", "IPC").encode("utf-8")
IPC_HOST = os.environ.get("IPC_HOST", "localhost")
IPC_PORT = int(os.environ.get("IPC_PORT", 6650))
IPC_ADDRESS: Tuple[str, int] = (IPC_HOST, IPC_PORT)
WORKER_COUNT = os.environ.get("WORKER_COUNT", 4)

ELASTICSEARCH_HOSTS = os.environ.get("ELASTICSEARCH_HOSTS", "localhost:9200").split(",")
ELASTICSEARCH_TYPE = "document"

ELASTICSEARCH_CATEGORY_INDEX = "category"
ELASTICSEARCH_PRODUCT_INDEX = "product"
ELASTICSEARCH_PRODUCT_EXTENDED_INDEX = "product_extended"
ELASTICSEARCH_CATEGORY_INDEX_CONFIG_PATH = (
    PROJECT_DIR / "robotoff/elasticsearch/index/category_index.json"
)
ELASTICSEARCH_PRODUCT_INDEX_CONFIG_PATH = (
    PROJECT_DIR / "robotoff/elasticsearch/index/product_index.json"
)

SLACK_TOKEN = os.environ.get("SLACK_TOKEN", "")
SLACK_OFF_TEST_CHANNEL = "CGLCKGVHS"
SLACK_OFF_ROBOTOFF_ALERT_CHANNEL = "CGKPALRCG"
SLACK_OFF_ROBOTOFF_USER_ALERT_CHANNEL = "CGWSXDGSF"
SLACK_OFF_ROBOTOFF_PRIVATE_IMAGE_ALERT_CHANNEL = "GGMRWLEF2"
SLACK_OFF_ROBOTOFF_PUBLIC_IMAGE_ALERT_CHANNEL = "CT2N423PA"
SLACK_OFF_NUTRISCORE_ALERT_CHANNEL = "CJZNFCSNP"

SENTRY_DSN = os.environ.get("SENTRY_DSN")

OCR_DATA_DIR = DATA_DIR / "ocr"
OCR_BRANDS_PATH = OCR_DATA_DIR / "brand.txt"
OCR_TAXONOMY_BRANDS_PATH = OCR_DATA_DIR / "brand_from_taxonomy.txt"
OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH = OCR_DATA_DIR / "brand_logo_annotation.txt"
OCR_STORES_DATA_PATH = OCR_DATA_DIR / "store_regex.txt"
OCR_STORES_NOTIFY_DATA_PATH = OCR_DATA_DIR / "store_notify.txt"
OCR_LOGO_ANNOTATION_LABELS_DATA_PATH = OCR_DATA_DIR / "label_logo_annotation.txt"
OCR_LABEL_FLASHTEXT_DATA_PATH = OCR_DATA_DIR / "label_flashtext.txt"
OCR_LABEL_WHITELIST_DATA_PATH = OCR_DATA_DIR / "label_whitelist.txt"
OCR_FISHING_FLASHTEXT_DATA_PATH = OCR_DATA_DIR / "fishing_flashtext.txt"
OCR_TAXONOMY_BRANDS_BLACKLIST_PATH = OCR_DATA_DIR / "brand_taxonomy_blacklist.txt"
OCR_IMAGE_FLAG_BEAUTY_PATH = OCR_DATA_DIR / "image_flag_beauty.txt"
OCR_IMAGE_FLAG_MISCELLANEOUS_PATH = OCR_DATA_DIR / "image_flag_miscellaneous.txt"
OCR_PACKAGING_DATA_PATH = OCR_DATA_DIR / "packaging.txt"
OCR_TRACE_ALLERGEN_DATA_PATH = OCR_DATA_DIR / "trace_allergen.txt"


BRAND_PREFIX_PATH = DATA_DIR / "brand_prefix.json"

ROBOTOFF_USER_AGENT = "Robotoff Live Analysis"
# Models and ML

MODELS_DIR = PROJECT_DIR / "models"

TF_SERVING_HOST = "localhost"
TF_SERVING_HTTP_PORT = "8501"
TF_SERVING_MODELS_PATH = PROJECT_DIR / "tf_models"
OBJECT_DETECTION_IMAGE_MAX_SIZE = (1024, 1024)

CATEGORY_CLF_MODEL_PATH = MODELS_DIR / "category" / "checkpoint.hdf5"
CATEGORY_CLF_CATEGORY_BLACKLIST = DATA_DIR / "clf_category_blacklist.txt"

OBJECT_DETECTION_TF_SERVING_MODELS = (
    "nutriscore",
    "nutrition-table",
    "universal-logo-detector",
)

BRAND_MATCHING_MIN_LENGTH = 4
BRAND_MATCHING_MIN_COUNT = 15

INFLUXDB_HOST = "localhost"
INFLUXDB_PORT = 8086
INFLUXDB_DB_NAME = "off_metrics"
INFLUXDB_USERNAME = "off_metrics"
INFLUXDB_PASSWORD = os.environ.get("INFLUXDB_PASSWORD")
