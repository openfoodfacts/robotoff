import datetime
import logging
from typing import Iterable, Iterator, Optional
from urllib.parse import urlparse

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from peewee import fn
from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import JSONDecodeError, SSLError, Timeout

from robotoff import settings
from robotoff.models import ProductInsight, with_db
from robotoff.types import ServerType
from robotoff.utils import get_logger, http_session

logger = get_logger(__name__)

URL_PATHS: list[str] = [
    "/ingredients-analysis?json=1",
    "/data-quality?json=1",
    "/ingredients?stats=1&json=1",
    "/states?json=1",
    "/misc?json=1",
]

COUNTRY_TAGS = [
    "world",
    "us",
    "uk",
    "fr",
    "es",
    "it",
    "be",
    "nl",
    "de",
    "ch",
    "be",
    "ca",
    "au",
    "mx",
    "at",
    "ie",
    "pl",
    "pt",
    "se",
    "ru",
    "th",
    "ma",
    "lu",
    "re",
    "ro",
    "bg",
    "hu",
    "dz",
    "dk",
    "br",
    "cz",
    "sg",
    "fi",
    "ar",
    "gd",
    "jp",
    "no",
    "in",
    "tn",
    "dk",
]


def get_influx_client() -> Optional[InfluxDBClient]:
    if not settings.INFLUXDB_HOST:
        return None
    return InfluxDBClient(
        url=f"http://{settings.INFLUXDB_HOST}:{settings.INFLUXDB_PORT}",
        token=settings.INFLUXDB_AUTH_TOKEN,
        org=settings.INFLUXDB_ORG,
    )


def ensure_influx_database():
    client = get_influx_client()
    if client is not None:
        try:
            bucket_client = client.buckets_api()
            bucket_names = [
                bucket.name for bucket in bucket_client.find_buckets().buckets
            ]
            if settings.INFLUXDB_BUCKET not in bucket_names:
                # create it
                client.bucket_name(bucket_name=settings.INFLUXDB_BUCKET)
                logger.warning(
                    "Creating influxdb bucket %r as it does not exist yet",
                    settings.INFLUXDB_BUCKET,
                )
        except Exception:
            # better be fail safe, our job is not that important !
            logger.exception("Error on ensure_influx_database")


def get_product_count(server_type: ServerType, country_tag: str) -> int:
    """Return the number of products in Product Opener for a specific country.

    :param country_tag: ISO 2-letter country code
    :return: the number of products currently in Product Opener
    """
    r = http_session.get(
        settings.BaseURLProvider.country(server_type, country_tag)
        + "/3.json?fields=null",
        auth=settings._off_request_auth,
    ).json()
    return int(r["count"])


def save_facet_metrics():
    # Only support for off for now
    server_type = ServerType.off
    inserts = []
    target_datetime = datetime.datetime.now()

    for country_tag in COUNTRY_TAGS:
        try:
            count = get_product_count(server_type, country_tag)
        except Exception:
            logger.exception("Error during product count retrieval for %s", country_tag)
            count = None

        for url_path in URL_PATHS:
            try:
                inserts += generate_metrics_from_path(
                    server_type, country_tag, url_path, target_datetime, count
                )
            except Exception:
                logger.exception()

        try:
            inserts += generate_metrics_from_path(
                server_type,
                country_tag,
                "/entry-date/{}/contributors?json=1".format(
                    # get contribution metrics for the previous day
                    (target_datetime - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                ),
                target_datetime,
                facet="contributors",
            )
        except Exception:
            logger.exception()

    try:
        inserts += generate_metrics_from_path(
            server_type, "world", "/countries?json=1", target_datetime
        )
    except Exception:
        logger.exception()
    client = get_influx_client()
    if client is not None:
        write_client = client.write_api(write_options=SYNCHRONOUS)
        write_client.write(bucket=settings.INFLUXDB_BUCKET, record=inserts)


def get_facet_name(url: str) -> str:
    return urlparse(url)[2].strip("/").replace("-", "_")


def generate_metrics_from_path(
    server_type: ServerType,
    country_tag: str,
    path: str,
    target_datetime: datetime.datetime,
    count: Optional[int] = None,
    facet: Optional[str] = None,
) -> list[dict]:
    inserts: list[dict] = []
    url = settings.BaseURLProvider.country(server_type, country_tag + "-en") + path

    if facet is None:
        facet = get_facet_name(url)

    try:
        r = http_session.get(url, timeout=60, auth=settings._off_request_auth)
    except (RequestConnectionError, SSLError, Timeout) as e:
        logger.info("Error during metrics retrieval: url=%s", url, exc_info=e)
        return inserts

    if not r.ok:
        logger.log(
            logging.INFO if r.status_code < 500 else logging.WARNING,
            "HTTPError during metrics retrieval: url=%s, %s",
            url,
            r.status_code,
        )
        return inserts

    try:
        data = r.json()
    except JSONDecodeError as e:
        logger.info("Error during OFF request JSON decoding:\n%s", e)
        return inserts

    for tag in data["tags"]:
        name = tag["name"]
        products = tag["products"]
        fields = {"products": products}

        if "percent" in tag:
            fields["percent"] = float(tag["percent"])

        elif count is not None:
            fields["percent"] = products * 100 / count

        tag_id = tag["id"]

        inserts.append(
            {
                "measurement": "facets",
                "tags": {
                    "tag_name": name,
                    "tag_id": tag_id,
                    "country": country_tag,
                    "facet": facet,
                },
                "time": target_datetime.isoformat(),
                "fields": fields,
            }
        )
    return inserts


def save_insight_metrics():
    """Save number of insights, grouped by the following fields:
    - type
    - annotation
    - automatic_processing
    - predictor
    - reserved_barcode
    - server_type
    """
    target_datetime = datetime.datetime.now()

    if (client := get_influx_client()) is not None:
        write_client = client.write_api(write_options=SYNCHRONOUS)
        inserts = generate_insight_metrics(target_datetime)
        write_client.write(bucket=settings.INFLUXDB_BUCKET, record=inserts)


@with_db
def generate_insight_metrics(target_datetime: datetime.datetime) -> list[dict]:
    group_by_fields = [
        ProductInsight.type,
        ProductInsight.annotation,
        ProductInsight.automatic_processing,
        ProductInsight.predictor,
        ProductInsight.reserved_barcode,
        ProductInsight.server_type,
    ]
    inserts = []
    query_results = (
        ProductInsight.select(
            *group_by_fields,
            fn.COUNT(ProductInsight.id).alias("count"),
        )
        .group_by(*group_by_fields)
        .dicts()
    )
    total_count = sum(query_result["count"] for query_result in query_results)

    for query_result in query_results:
        count = query_result.pop("count")
        inserts.append(
            {
                "measurement": "insights",
                "tags": query_result,
                "time": target_datetime.isoformat(),
                "fields": {"count": count, "percent": count / total_count},
            }
        )
    return inserts


def generate_recent_changes_metrics(items: Iterable[dict]) -> Iterator[dict]:
    for item in items:
        comment: str = item["comment"]
        diffs: dict = item["diffs"]
        uploaded_images = diffs.setdefault("uploaded_images", {})
        selected_images: dict = diffs.setdefault("selected_images", {})
        nutriments: dict = diffs.setdefault("nutriments", {})
        nutriments_add: dict = nutriments.get("add", {})
        nutriments_change: dict = nutriments.get("change", {})
        nutriments_delete: dict = nutriments.get("delete", {})
        fields: dict = diffs.setdefault("fields", {})
        fields_add: dict = fields.setdefault("add", {})
        fields_change: dict = fields.setdefault("change", {})
        packagings: dict = diffs.setdefault("packagings", {})
        yield {
            "measurement": "recent_changes",
            "tags": {
                "countries_tags": item["countries_tags"],
                "user_id": item["userid"],
                "is_smooth_app": int("Smoothie - OpenFoodFacts" in comment),
                "by_robotoff": int("[robotoff]" in comment),
                "has_image_upload": int(bool(uploaded_images.get("add", {}))),
                "has_image_delete": int(bool(uploaded_images.get("delete", {}))),
                "has_image_selection_change": int(
                    bool(selected_images.get("change", {}))
                ),
                "has_image_selection_add": int(bool(selected_images.get("add", {}))),
                "has_image_selection_delete": int(
                    bool(selected_images.get("delete", {}))
                ),
                "has_nutriment_change": int(bool(nutriments_change)),
                "has_nutriment_add": int(bool(nutriments_add)),
                "has_nutriment_delete": int(bool(nutriments_delete)),
                "has_nutriscore_added": int("nutrition-score-fr" in nutriments_add),
                "has_nutriscore_change": int("nutrition-score-fr" in nutriments_change),
                "has_nutriscore_delete": int("nutrition-score-fr" in nutriments_delete),
                "has_categories_add": int("categories" in fields_add),
                "has_categories_change": int("categories" in fields_change),
                "has_packagings_add": int(bool(packagings.get("add", {}))),
                "has_packagings_change": int(bool(packagings.get("change", {}))),
            },
            "time": item["t"],
            "fields": {"count": 1},
        }
