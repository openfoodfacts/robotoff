import datetime
from urllib.parse import urlparse
from typing import List

from influxdb import InfluxDBClient
import requests

from robotoff import settings
from datetime import date

today = date.today()
date = today.strftime("%y-%m-%d")

URL_PATHS: List[str] = [
    "/ingredients-analysis?json=1",
    "/data-quality?json=1",
    "/ingredients?stats=1&json=1",
    "/states?json=1",
    "/countries?json=1",
    "/entry-date/"+date+"/contributors?json=1",
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
]


def get_influx_client() -> InfluxDBClient:
    return InfluxDBClient(
        settings.INFLUXDB_HOST,
        settings.INFLUXDB_PORT,
        settings.INFLUXDB_USERNAME,
        settings.INFLUXDB_PASSWORD,
        settings.INFLUXDB_DB_NAME,
    )


def save_facet_metrics():
    client = get_influx_client()

    inserts = []
    target_datetime = datetime.datetime.now()

    for url_path in URL_PATHS:
        for country_tag in COUNTRY_TAGS:
            if country_tag != "world" and url_path.startswith("/countries"):
                continue

            inserts += generate_metrics_from_path(
                country_tag, url_path, target_datetime
            )

    client.write_points(inserts)


def get_facet_name(url: str) -> str:
    return urlparse(url)[2].strip("/").replace("-", "_")


def generate_metrics_from_path(
    country_tag: str, path: str, target_datetime: datetime.datetime
) -> List:
    url = f"https://{country_tag}-en.openfoodfacts.org{path}"
    facet = get_facet_name(url)
    data = requests.get(url).json()

    inserts = []
    for tag in data["tags"]:
        name = tag["name"]
        products = tag["products"]
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
                "fields": {"products": products},
            }
        )
    return inserts
