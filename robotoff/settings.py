import os
from pathlib import Path
from typing import Dict, Sequence, Tuple

import sentry_sdk
from sentry_sdk.integrations import Integration

_robotoff_instance = os.environ.get("ROBOTOFF_INSTANCE", "dev")


# Returns the top-level-domain (TLD) for the Robotoff instance.
def _instance_tld() -> str:
    if _robotoff_instance == "prod":
        return "org"
    elif _robotoff_instance == "dev":
        return "net"
    else:
        return _robotoff_instance


_default_robotoff_domain = f"openfoodfacts.{_instance_tld()}"
_robotoff_domain = os.environ.get("ROBOTOFF_DOMAIN", _default_robotoff_domain)


class BaseURLProvider(object):
    """BaseURLProvider allows to fetch a base URL for Product Opener/Robotoff.

    Example usage: BaseURLProvider().robotoff().get() returns the Robotoff URL.
    """

    def __init__(self):
        self.domain = os.environ.get(
            "ROBOTOFF_DOMAIN", "openfoodfacts.%s" % _instance_tld()
        )
        self.url = "%(scheme)s://%(prefix)s.%(domain)s"
        self.prefix = "world"
        self.scheme = os.environ.get("ROBOTOFF_SCHEME", "https")

    def robotoff(self):
        self.prefix = "robotoff"
        return self

    def static(self):
        self.prefix = "static"
        # locally we may want to change it, give environment a chance
        static_domain = os.environ.get("STATIC_OFF_DOMAIN", "")
        if static_domain:
            if "://" in static_domain:
                self.scheme, static_domain = static_domain.split("://", 1)
            self.domain = static_domain
        return self

    def country(self, country_code: str):
        self.prefix = country_code
        return self

    def get(self):
        return self.url % {
            "scheme": self.scheme,
            "prefix": self.prefix,
            "domain": self.domain,
        }


PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATASET_DIR = PROJECT_DIR / "datasets"
DATASET_DIR.mkdir(exist_ok=True)
I18N_DIR = PROJECT_DIR / "i18n"
JSONL_DATASET_PATH = DATASET_DIR / "products.jsonl.gz"
JSONL_DATASET_ETAG_PATH = DATASET_DIR / "products-etag.txt"
JSONL_MIN_DATASET_PATH = DATASET_DIR / "products-min.jsonl.gz"
DATASET_CHECK_MIN_PRODUCT_COUNT = 1000000

# Products JSONL

JSONL_DATASET_URL = (
    BaseURLProvider().static().get() + "/data/openfoodfacts-products.jsonl.gz"
)

TAXONOMY_CATEGORY_URL = (
    BaseURLProvider().static().get() + "/data/taxonomies/categories.full.json"
)
TAXONOMY_INGREDIENT_URL = (
    BaseURLProvider().static().get() + "/data/taxonomies/ingredients.full.json"
)
TAXONOMY_LABEL_URL = (
    BaseURLProvider().static().get() + "/data/taxonomies/labels.full.json"
)
TAXONOMY_BRAND_URL = (
    BaseURLProvider().static().get() + "/data/taxonomies/brands.full.json"
)
OFF_IMAGE_BASE_URL = BaseURLProvider().static().get() + "/images/products"

OFF_BRANDS_URL = BaseURLProvider().get() + "/brands.json"

_off_password = os.environ.get("OFF_PASSWORD", "")
_off_user = os.environ.get("OFF_USER", "")


def off_credentials() -> Dict:
    return {"user_id": _off_user, "password": _off_password}


OFF_SERVER_DOMAIN = "api." + BaseURLProvider().domain

# Taxonomies are huge JSON files that describe many concepts in OFF, in many languages, with synonyms. Those are the full version of taxos.

TAXONOMY_DIR = DATA_DIR / "taxonomies"
TAXONOMY_CATEGORY_PATH = TAXONOMY_DIR / "categories.full.json"
TAXONOMY_INGREDIENT_PATH = TAXONOMY_DIR / "ingredients.full.json"
TAXONOMY_LABEL_PATH = TAXONOMY_DIR / "labels.full.json"
TAXONOMY_BRAND_PATH = TAXONOMY_DIR / "brands.full.json"
INGREDIENTS_FR_PATH = TAXONOMY_DIR / "ingredients_fr.txt"
INGREDIENT_TOKENS_PATH = TAXONOMY_DIR / "ingredients_tokens.txt"
FR_TOKENS_PATH = TAXONOMY_DIR / "fr_tokens_lower.gz"

# Spellchecking parameters. Wauplin and Raphael are the experts.

SPELLCHECK_DIR = DATA_DIR / "spellcheck"
SPELLCHECK_PATTERNS_PATHS = {
    "fr": SPELLCHECK_DIR / "patterns_fr.txt",
}

# Credentials for the Robotoff insights database

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")

# Mongo used to be on the same server as Robotoff

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017")

IPC_AUTHKEY = os.environ.get("IPC_AUTHKEY", "IPC").encode("utf-8")
IPC_HOST = os.environ.get("IPC_HOST", "localhost")
IPC_PORT = int(os.environ.get("IPC_PORT", 6650))
IPC_ADDRESS: Tuple[str, int] = (IPC_HOST, IPC_PORT)
WORKER_COUNT = int(os.environ.get("WORKER_COUNT", 8))
# how many seconds should we wait to compute insight on product updated
UPDATED_PRODUCT_WAIT = float(os.environ.get("ROBOTOFF_UPDATED_PRODUCT_WAIT", 10))

# Elastic Search is used for simple category prediction and spellchecking.

ELASTICSEARCH_HOSTS = os.environ.get("ELASTICSEARCH_HOSTS", "localhost:9200").split(",")
ELASTICSEARCH_TYPE = "document"


class ElasticsearchIndex:
    CATEGORY = "category"
    PRODUCT = "product"

    SUPPORTED_INDICES = {
        CATEGORY: (PROJECT_DIR / "robotoff/elasticsearch/index/category_index.json"),
        PRODUCT: (PROJECT_DIR / "robotoff/elasticsearch/index/product_index.json"),
    }


# Slack paramaters for notifications about detection
_slack_token = os.environ.get("SLACK_TOKEN", "")


# Returns the slack token to use for posting alerts if the current instance is the 'prod' instance.
# For all other instances, the empty string is returned.
def slack_token() -> str:
    if _robotoff_instance == "prod":
        if _slack_token != "":
            return _slack_token
        else:
            raise ValueError("No SLACK_TOKEN specified for prod Robotoff")

    if _slack_token != "":
        raise ValueError("SLACK_TOKEN specified for non-prod Robotoff")
    return ""


# Sentry for error reporting
_sentry_dsn = os.environ.get("SENTRY_DSN")


def init_sentry(integrations: Sequence[Integration] = ()):
    if _sentry_dsn:
        sentry_sdk.init(
            _sentry_dsn,
            environment=_robotoff_instance,
            integrations=integrations,
        )
    elif _robotoff_instance == "prod":
        raise ValueError("No SENTRY_DSN specified for prod Robotoff")


OCR_DATA_DIR = DATA_DIR / "ocr"
OCR_BRANDS_PATH = OCR_DATA_DIR / "brand.txt"
OCR_TAXONOMY_BRANDS_PATH = OCR_DATA_DIR / "brand_from_taxonomy.txt"
OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH = OCR_DATA_DIR / "brand_logo_annotation.txt"
OCR_STORES_DATA_PATH = OCR_DATA_DIR / "store_regex.txt"
OCR_STORES_NOTIFY_DATA_PATH = OCR_DATA_DIR / "store_notify.txt"
OCR_LOGO_ANNOTATION_LABELS_DATA_PATH = OCR_DATA_DIR / "label_logo_annotation.txt"
OCR_LABEL_FLASHTEXT_DATA_PATH = OCR_DATA_DIR / "label_flashtext.txt"
OCR_LABEL_WHITELIST_DATA_PATH = OCR_DATA_DIR / "label_whitelist.txt"
# Try to detect MSC codes
OCR_FISHING_FLASHTEXT_DATA_PATH = OCR_DATA_DIR / "fishing_flashtext.txt"
OCR_TAXONOMY_BRANDS_BLACKLIST_PATH = OCR_DATA_DIR / "brand_taxonomy_blacklist.txt"
# Try to detect cosmetics in OFF
OCR_IMAGE_FLAG_BEAUTY_PATH = OCR_DATA_DIR / "image_flag_beauty.txt"
OCR_IMAGE_FLAG_MISCELLANEOUS_PATH = OCR_DATA_DIR / "image_flag_miscellaneous.txt"
OCR_PACKAGING_DATA_PATH = OCR_DATA_DIR / "packaging.txt"
OCR_TRACE_ALLERGEN_DATA_PATH = OCR_DATA_DIR / "trace_allergen.txt"
# Try to detect postal codes in France
OCR_CITIES_FR_PATH = OCR_DATA_DIR / "cities_laposte_hexasmal.json.gz"

BRAND_PREFIX_PATH = DATA_DIR / "brand_prefix.json"

# When we're making queries to the API, so that we're not blocked by error
ROBOTOFF_USER_AGENT = "Robotoff Live Analysis"
# Models and ML

MODELS_DIR = PROJECT_DIR / "models"

# Tensorflow Serving host parameters

_tf_serving_host = os.environ.get("TF_SERVING_HOST", "localhost")
_tf_serving_http_port = os.environ.get("TF_SERVING_PORT", "8501")
TF_SERVING_BASE_URL = f"http://{_tf_serving_host}:{_tf_serving_http_port}/v1/models"

TF_SERVING_MODELS_PATH = PROJECT_DIR / "tf_models"
OBJECT_DETECTION_IMAGE_MAX_SIZE = (1024, 1024)


OBJECT_DETECTION_TF_SERVING_MODELS = (
    "nutriscore",
    "nutrition-table",
    "universal-logo-detector",
)

OBJECT_DETECTION_MODEL_VERSION = {
    "nutriscore": "tf-nutriscore-1.0",
    "nutrition-table": "tf-nutrition-table-1.0",
    "universal-logo-detector": "tf-universal-logo-detector-1.0",
}

# We require a minimum of 15 occurences of the brands already on OFF to perform the extraction. This reduces false positive.
# We require a minimum of 4 characters for the brand

BRAND_MATCHING_MIN_LENGTH = 4
BRAND_MATCHING_MIN_COUNT = 15

INFLUXDB_HOST = os.environ.get("INFLUXDB_HOST", "localhost")
INFLUXDB_PORT = int(os.environ.get("INFLUXDB_PORT", "8086"))
INFLUXDB_DB_NAME = os.environ.get("INFLUXDB_DB_NAME", "off_metrics")
INFLUXDB_USERNAME = os.environ.get("INFLUXDB_USERNAME", "off_metrics")
INFLUXDB_PASSWORD = os.environ.get("INFLUXDB_PASSWORD")

TEST_DIR = PROJECT_DIR / "tests"
TEST_DATA_DIR = TEST_DIR / "unit/data"
