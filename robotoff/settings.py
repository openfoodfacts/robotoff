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
def _robotoff_instance():
    return os.environ.get("ROBOTOFF_INSTANCE", "dev")


# Returns the top-level-domain (TLD) for the Robotoff instance.
def _instance_tld() -> str:
    robotoff_instance = _robotoff_instance()
    if robotoff_instance == "prod":
        return "org"
    elif robotoff_instance == "dev":
        return "net"
    else:
        return robotoff_instance


def _get_default_scheme() -> str:
    return os.environ.get("ROBOTOFF_SCHEME", "https")


def _get_default_domain():
    # `ROBOTOFF_DOMAIN` can be used to overwrite the Product Opener domain used.
    # If empty, the domain will be inferred from `ROBOTOFF_INSTANCE`
    return os.environ.get("ROBOTOFF_DOMAIN", "openfoodfacts.%s" % _instance_tld())


class BaseURLProvider(object):
    """BaseURLProvider allows to fetch a base URL for Product Opener/Robotoff.

    Example usage: BaseURLProvider.robotoff() returns the Robotoff URL.
    """

    @staticmethod
    def _get_url(
        prefix: Optional[str] = "world",
        domain: Optional[str] = None,
        scheme: Optional[str] = None,
    ):
        data = {
            "domain": _get_default_domain(),
            "scheme": _get_default_scheme(),
        }
        if prefix:
            data["prefix"] = prefix
        if scheme:
            data["scheme"] = scheme
        if domain:
            data["domain"] = domain

        if "prefix" in data:
            return "%(scheme)s://%(prefix)s.%(domain)s" % data

        return "%(scheme)s://%(domain)s" % data

    @staticmethod
    def server_domain():
        """Return the server domain: `api.openfoodfacts.*`"""
        return "api." + _get_default_domain()

    @staticmethod
    def world():
        return BaseURLProvider._get_url(prefix="world")

    @staticmethod
    def robotoff() -> str:
        return BaseURLProvider._get_url(prefix="robotoff")

    @staticmethod
    def api() -> str:
        return BaseURLProvider._get_url(prefix="api")

    @staticmethod
    def static() -> str:
        # locally we may want to change it, give environment a chance
        static_domain = os.environ.get("STATIC_OFF_DOMAIN", "")
        if static_domain:
            if "://" in static_domain:
                scheme, static_domain = static_domain.split("://", 1)
            else:
                scheme = _get_default_scheme()
            return BaseURLProvider._get_url(
                prefix=None, scheme=scheme, domain=static_domain
            )

        return BaseURLProvider._get_url(prefix="static")

    @staticmethod
    def image_url(image_path: str) -> str:
        # If STATIC_OFF_DOMAIN is defined, used the custom static domain
        # configured
        # Otherwise use images.openfoodfacts.{net,org} as proxy server
        prefix = (
            BaseURLProvider.static()
            if os.environ.get("STATIC_OFF_DOMAIN")
            else BaseURLProvider._get_url(prefix="images")
        )
        return prefix + f"/images/products{image_path}"

    @staticmethod
    def country(country_code: str) -> str:
        return BaseURLProvider._get_url(prefix=country_code)

    @staticmethod
    def event_api() -> str:
        return os.environ.get(
            "EVENTS_API_URL", BaseURLProvider._get_url(prefix="events")
        )


PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATASET_DIR = PROJECT_DIR / "datasets"
DATASET_DIR.mkdir(exist_ok=True)
I18N_DIR = PROJECT_DIR / "i18n"
LABEL_LOGOS_PATH = DATA_DIR / "label_logos.json"
GRAMMARS_DIR = DATA_DIR / "grammars"
JSONL_DATASET_PATH = DATASET_DIR / "products.jsonl.gz"
JSONL_DATASET_ETAG_PATH = DATASET_DIR / "products-etag.txt"
JSONL_MIN_DATASET_PATH = DATASET_DIR / "products-min.jsonl.gz"
DATASET_CHECK_MIN_PRODUCT_COUNT = 1000000

# Products JSONL

JSONL_DATASET_URL = BaseURLProvider.static() + "/data/openfoodfacts-products.jsonl.gz"

TAXONOMY_URLS = {
    "category": BaseURLProvider.static() + "/data/taxonomies/categories.full.json",
    "ingredient": BaseURLProvider.static() + "/data/taxonomies/ingredients.full.json",
    "label": BaseURLProvider.static() + "/data/taxonomies/labels.full.json",
    "brand": BaseURLProvider.static() + "/data/taxonomies/brands.full.json",
    "packaging_shape": BaseURLProvider.static()
    + "/data/taxonomies/packaging_shapes.full.json",
    "packaging_material": BaseURLProvider.static()
    + "/data/taxonomies/packaging_materials.full.json",
    "packaging_recycling": BaseURLProvider.static()
    + "/data/taxonomies/packaging_recycling.full.json",
}

_off_password = os.environ.get("OFF_PASSWORD", "")
_off_user = os.environ.get("OFF_USER", "")
_off_request_auth = ("off", "off") if _instance_tld() == "net" else None


CATEGORY_MATCHER_DIR = DATA_DIR / "category/matcher"
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
    "packaging_material": TAXONOMY_DIR / "packaging_materials.full.json.gz",
    "packaging_shape": TAXONOMY_DIR / "packaging_shapes.full.json.gz",
    "packaging_recycling": TAXONOMY_DIR / "packaging_recycling.full.json.gz",
}
INGREDIENTS_FR_PATH = TAXONOMY_DIR / "ingredients_fr.txt"
INGREDIENT_TOKENS_PATH = TAXONOMY_DIR / "ingredients_tokens.txt"
FR_TOKENS_PATH = TAXONOMY_DIR / "fr_tokens_lower.gz"

# Spellchecking parameters. Wauplin and Raphael are the experts.

SPELLCHECK_DIR = DATA_DIR / "spellcheck"
SPELLCHECK_PATTERNS_PATHS = {"fr": SPELLCHECK_DIR / "patterns_fr.txt"}

# Credentials for the Robotoff insights database

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")

# Mongo used to be on the same server as Robotoff

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")

# Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")

# how many seconds should we wait to compute insight on product updated
UPDATED_PRODUCT_WAIT = float(os.environ.get("ROBOTOFF_UPDATED_PRODUCT_WAIT", 10))

# Elastic Search is used for simple category prediction, spellchecking and logo classification.

ELASTIC_HOST = os.environ.get("ELASTIC_HOST", "localhost")
ELASTIC_USER = os.environ.get("ELASTIC_USER", "elastic")
ELASTIC_PASSWORD = os.environ.get("ELASTIC_PASSWORD", "elastic")
ELASTICSEARCH_TYPE = "document"


# ANN index parameters
K_NEAREST_NEIGHBORS = 100

# image moderation service
IMAGE_MODERATION_SERVICE_URL: Optional[str] = os.environ.get(
    "IMAGE_MODERATION_SERVICE_URL", None
)

# Slack paramaters for notifications about detection
_slack_token = os.environ.get("SLACK_TOKEN", "")


# Returns the slack token to use for posting alerts if the current instance is the 'prod' instance.
# For all other instances, the empty string is returned.
def slack_token() -> str:
    if _robotoff_instance() == "prod":
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
    robotoff_instance = _robotoff_instance()
    if _sentry_dsn:
        integrations = integrations or []
        integrations.append(
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.WARNING,  # Send warning and errors as events
            )
        )
        sentry_sdk.init(  # type:ignore # mypy say it's abstract
            _sentry_dsn, environment=robotoff_instance, integrations=integrations
        )
    elif robotoff_instance == "prod":
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

# Number of minutes to wait before processing an insight automatically
INSIGHT_AUTOMATIC_PROCESSING_WAIT = int(
    os.environ.get("INSIGHT_AUTOMATIC_PROCESSING_WAIT", 10)
)
