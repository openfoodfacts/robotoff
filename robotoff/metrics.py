import datetime
import json
from typing import List, Optional
from urllib.parse import urlparse

import requests
from influxdb import InfluxDBClient

from robotoff import settings
from robotoff.utils import get_logger

logger = get_logger(__name__)

URL_PATHS: List[str] = [
    "/ingredients-analysis?json=1",
    "/data-quality?json=1",
    "/ingredients?stats=1&json=1",
    "/states?json=1",
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
    "po",
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
    "da",
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


def get_influx_client() -> InfluxDBClient:
    if not settings.INFLUXDB_HOST:
        return None
    return InfluxDBClient(
        settings.INFLUXDB_HOST,
        settings.INFLUXDB_PORT,
        settings.INFLUXDB_USERNAME,
        settings.INFLUXDB_PASSWORD,
        settings.INFLUXDB_DB_NAME,
    )


def get_product_count(country_tag: str) -> int:
    r = requests.get(
        settings.BaseURLProvider().country(country_tag).get() + "/3.json?fields=null"
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
        client.write_points(inserts)


def get_facet_name(url: str) -> str:
    return urlparse(url)[2].strip("/").replace("-", "_")


def generate_metrics_from_path(
    country_tag: str,
    path: str,
    target_datetime: datetime.datetime,
    count: Optional[int] = None,
    facet: Optional[str] = None,
) -> List:
    inserts: List = []
    url = settings.BaseURLProvider().country(country_tag + "-en").get() + path

    if facet is None:
        facet = get_facet_name(url)

    try:
        r = requests.get(url, timeout=60)
    except requests.exceptions.Timeout:
        logger.error("OFF request timeout (60s): {}".format(url))
        return inserts

    if not r.ok:
        logger.error("Error during OFF request: {}".format(r.status_code))
        return inserts

    try:
        data = r.json()
    except json.JSONDecodeError as e:
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
