import datetime
from typing import Optional
from urllib.parse import urlparse

import requests
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from peewee import fn

from robotoff import settings
from robotoff.models import ProductInsight, with_db
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


def get_product_count(country_tag: str) -> int:
    r = http_session.get(
        settings.BaseURLProvider().country(country_tag).get() + "/3.json?fields=null",
        auth=settings._off_request_auth,
    ).json()
    return int(r["count"])


def save_facet_metrics():
    inserts = []
    target_datetime = datetime.datetime.now()
    product_counts = {
        country_tag: get_product_count(country_tag) for country_tag in COUNTRY_TAGS
    }

    for country_tag in COUNTRY_TAGS:
        count = product_counts[country_tag]

        for url_path in URL_PATHS:
            inserts += generate_metrics_from_path(
                country_tag, url_path, target_datetime, count
            )

        inserts += generate_metrics_from_path(
            country_tag,
            "/entry-date/{}/contributors?json=1".format(
                # get contribution metrics for the previous day
                (target_datetime - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            ),
            target_datetime,
            facet="contributors",
        )

    inserts += generate_metrics_from_path("world", "/countries?json=1", target_datetime)
    client = get_influx_client()
    if client is not None:
        write_client = client.write_api(write_options=SYNCHRONOUS)
        write_client.write(bucket=settings.INFLUXDB_BUCKET, record=inserts)


def get_facet_name(url: str) -> str:
    return urlparse(url)[2].strip("/").replace("-", "_")


def generate_metrics_from_path(
    country_tag: str,
    path: str,
    target_datetime: datetime.datetime,
    count: Optional[int] = None,
    facet: Optional[str] = None,
) -> list[dict]:
    inserts: list[dict] = []
    url = settings.BaseURLProvider().country(country_tag + "-en").get() + path

    if facet is None:
        facet = get_facet_name(url)

    try:
        r = http_session.get(url, timeout=60, auth=settings._off_request_auth)
    except requests.exceptions.Timeout:
        logger.error("OFF request timeout (60s): {}".format(url))
        return inserts

    if not r.ok:
        logger.error("Error during OFF request: {}".format(r.status_code))
        return inserts

    try:
        data = r.json()
    except requests.exceptions.JSONDecodeError as e:
        logger.error("Error during OFF request JSON decoding:\n{}".format(e))
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
