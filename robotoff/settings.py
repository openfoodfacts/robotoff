import copy
import datetime
import logging
import os
from pathlib import Path
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.logging import LoggingIntegration

# Robotoff instance gives the environment, either `prod` or `dev`
# (`dev` by default).
# If `prod` is used, openfoodfacts.org domain will be used by default,
# and openfoodfacts.net if `dev` is used.
# Messages to Slack are only enabled if `ROBOTOFF_INSTANCE=prod`.
ROBOTOFF_INSTANCE = os.environ.get("ROBOTOFF_INSTANCE", "dev")


# Returns the top-level-domain (TLD) for the Robotoff instance.
def _instance_tld() -> str:
    if ROBOTOFF_INSTANCE == "prod":
        return "org"
    elif ROBOTOFF_INSTANCE == "dev":
        return "net"
    else:
        return ROBOTOFF_INSTANCE


_default_robotoff_domain = f"openfoodfacts.{_instance_tld()}"

# `ROBOTOFF_DOMAIN` can be used to overwrite the Product Opener domain used.
# If empty, the domain will be inferred from `ROBOTOFF_INSTANCE`
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

    def clone(self):
        return copy.deepcopy(self)

    def robotoff(self):
        result = self.clone()
        result.prefix = "robotoff"
        return result

    def static(self):
        result = self.clone()
        result.prefix = "static"
        # locally we may want to change it, give environment a chance
        static_domain = os.environ.get("STATIC_OFF_DOMAIN", "")
        if static_domain:
            if "://" in static_domain:
                result.scheme, static_domain = static_domain.split("://", 1)
            result.domain = static_domain
        return result

    def country(self, country_code: str):
        result = self.clone()
        result.prefix = country_code
        return result

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
LABEL_LOGOS_PATH = DATA_DIR / "label_logos.json"
JSONL_DATASET_PATH = DATASET_DIR / "products.jsonl.gz"
JSONL_DATASET_ETAG_PATH = DATASET_DIR / "products-etag.txt"
JSONL_MIN_DATASET_PATH = DATASET_DIR / "products-min.jsonl.gz"
DATASET_CHECK_MIN_PRODUCT_COUNT = 1000000

# Products JSONL

JSONL_DATASET_URL = (
    BaseURLProvider().static().get() + "/data/openfoodfacts-products.jsonl.gz"
)

TAXONOMY_URLS = {
    "category": BaseURLProvider().static().get()
    + "/data/taxonomies/categories.full.json",
    "ingredient": BaseURLProvider().static().get()
    + "/data/taxonomies/ingredients.full.json",
    "label": BaseURLProvider().static().get() + "/data/taxonomies/labels.full.json",
    "brand": BaseURLProvider().static().get() + "/data/taxonomies/brands.full.json",
    "packaging_shape": BaseURLProvider().static().get()
    + "/data/taxonomies/packaging_shapes.full.json",
    "packaging_material": BaseURLProvider().static().get()
    + "/data/taxonomies/packaging_materials.full.json",
    "packaging_recycling": BaseURLProvider().static().get()
    + "/data/taxonomies/packaging_recycling.full.json",
}

OFF_IMAGE_BASE_URL = BaseURLProvider().static().get() + "/images/products"

_off_password = os.environ.get("OFF_PASSWORD", "")
_off_user = os.environ.get("OFF_USER", "")
_off_request_auth = ("off", "off") if _instance_tld() == "net" else None


def off_credentials() -> dict[str, str]:
    return {"user_id": _off_user, "password": _off_password}


OFF_SERVER_DOMAIN = "api." + BaseURLProvider().domain
EVENTS_API_URL = os.environ.get(
    "EVENTS_API_URL", "https://events." + BaseURLProvider().domain
)

CATEGORY_MATCHER_DIR = DATA_DIR / "category_matcher"
CATEGORY_MATCHER_MATCH_MAPS = {
    "category": CATEGORY_MATCHER_DIR / "category_match_maps.json.gz",
    "ingredient": CATEGORY_MATCHER_DIR / "ingredient_match_maps.json.gz",
}
CATEGORY_MATCHER_INTERSECT = (
    CATEGORY_MATCHER_DIR / "category_ingredient_intersect.json.gz"
)

# Taxonomies are huge JSON files that describe many concepts in OFF, in many languages, with synonyms. Those are the full version of taxos.

TAXONOMY_DIR = DATA_DIR / "taxonomies"
TAXONOMY_PATHS = {
    "category": TAXONOMY_DIR / "categories.full.json.gz",
    "ingredient": TAXONOMY_DIR / "ingredients.full.json.gz",
    "label": TAXONOMY_DIR / "labels.full.json.gz",
    "brand": TAXONOMY_DIR / "brands.full.json.gz",
}
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

# Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")

# how many seconds should we wait to compute insight on product updated
UPDATED_PRODUCT_WAIT = float(os.environ.get("ROBOTOFF_UPDATED_PRODUCT_WAIT", 10))

# Elastic Search is used for simple category prediction and spellchecking.

ELASTICSEARCH_HOSTS = os.environ.get("ELASTICSEARCH_HOSTS", "localhost:9200").split(",")
ELASTICSEARCH_TYPE = "document"


class ElasticsearchIndex:
    PRODUCT = "product"

    SUPPORTED_INDICES = {
        PRODUCT: (PROJECT_DIR / "robotoff/elasticsearch/index/product_index.json"),
    }


# image moderation service
IMAGE_MODERATION_SERVICE_URL: Optional[str] = os.environ.get(
    "IMAGE_MODERATION_SERVICE_URL", None
)

# Slack paramaters for notifications about detection
_slack_token = os.environ.get("SLACK_TOKEN", "")


# Returns the slack token to use for posting alerts if the current instance is the 'prod' instance.
# For all other instances, the empty string is returned.
def slack_token() -> str:
    if ROBOTOFF_INSTANCE == "prod":
        if _slack_token != "":
            return _slack_token
        else:
            raise ValueError("No SLACK_TOKEN specified for prod Robotoff")

    if _slack_token != "":
        raise ValueError("SLACK_TOKEN specified for non-prod Robotoff")
    return ""


# Sentry for error reporting
_sentry_dsn = os.environ.get("SENTRY_DSN")


def init_sentry(integrations: Optional[list[Integration]] = None):
    if _sentry_dsn:
        integrations = integrations or []
        integrations.append(
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.WARNING,  # Send warning and errors as events
            )
        )
        sentry_sdk.init(  # type:ignore # mypy say it's abstract
            _sentry_dsn,
            environment=ROBOTOFF_INSTANCE,
            integrations=integrations,
        )
    elif ROBOTOFF_INSTANCE == "prod":
        raise ValueError("No SENTRY_DSN specified for prod Robotoff")


OCR_DATA_DIR = DATA_DIR / "ocr"
OCR_BRANDS_PATH = OCR_DATA_DIR / "brand.txt"
OCR_TAXONOMY_BRANDS_PATH = OCR_DATA_DIR / "brand_from_taxonomy.gz"
OCR_LOGO_ANNOTATION_BRANDS_DATA_PATH = OCR_DATA_DIR / "brand_logo_annotation.txt"
OCR_STORES_DATA_PATH = OCR_DATA_DIR / "store_regex.txt"
OCR_STORES_NOTIFY_DATA_PATH = OCR_DATA_DIR / "store_notify.txt"
OCR_LOGO_ANNOTATION_LABELS_DATA_PATH = OCR_DATA_DIR / "label_logo_annotation.txt"
OCR_LABEL_FLASHTEXT_DATA_PATH = OCR_DATA_DIR / "label_flashtext.txt"
OCR_USDA_CODE_FLASHTEXT_DATA_PATH = OCR_DATA_DIR / "USDA_code_flashtext.txt"
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

BRAND_PREFIX_PATH = DATA_DIR / "brand_prefix.json.gz"

# When we're making queries to the API, so that we're not blocked by error
ROBOTOFF_USER_AGENT = "Robotoff Live Analysis"
# Models and ML

MODELS_DIR = PROJECT_DIR / "models"

# Tensorflow Serving host parameters

_tf_serving_host = os.environ.get("TF_SERVING_HOST", "localhost")
_tf_serving_http_port = os.environ.get("TF_SERVING_PORT", "8501")
TF_SERVING_BASE_URL = f"http://{_tf_serving_host}:{_tf_serving_http_port}/v1/models"


_triton_host = os.environ.get("TRITON_HOST", "localhost")
_triton_grpc_port = os.environ.get("TRITON_PORT", "8001")
TRITON_URI = f"{_triton_host}:{_triton_grpc_port}"

MODELS_DIR = PROJECT_DIR / "models"
OBJECT_DETECTION_IMAGE_MAX_SIZE = (1024, 1024)


# We require a minimum of 15 occurences of the brands already on OFF to perform the extraction. This reduces false positive.
# We require a minimum of 4 characters for the brand

BRAND_MATCHING_MIN_LENGTH = 4
BRAND_MATCHING_MIN_COUNT = 15

INFLUXDB_HOST = os.environ.get("INFLUXDB_HOST", "localhost")
INFLUXDB_PORT = int(os.environ.get("INFLUXDB_PORT", "8086"))
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "off_metrics")
INFLUXDB_AUTH_TOKEN = os.environ.get("INFLUXDB_AUTH_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "off")

TEST_DIR = PROJECT_DIR / "tests"
TEST_DATA_DIR = TEST_DIR / "unit/data"

# Maximum interval between the upload of the insight image and the upload of
# the most recent image of the product to consider the insight image as
# trustworthy. Insights with untrustworthy images cannot be applied
# automatically.
# For example if days=120, it means that an insight based on an image that is
# more than 120 days older than the most recent product image cannot be applied
# automatically.
IMAGE_MAX_TIMEDELTA = datetime.timedelta(days=120)

# Number of minutes to wait before processing an insight automatically
INSIGHT_AUTOMATIC_PROCESSING_WAIT = int(
    os.environ.get("INSIGHT_AUTOMATIC_PROCESSING_WAIT", 10)
)
