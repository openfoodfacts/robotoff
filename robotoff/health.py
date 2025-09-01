import logging

import requests
from healthcheck import HealthCheck
from influxdb_client import InfluxDBClient
from playhouse.postgres_ext import PostgresqlExtDatabase
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from redis import Redis
from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import JSONDecodeError, SSLError, Timeout

from robotoff import settings
from robotoff.elasticsearch import get_es_client

health = HealthCheck()

logger = logging.getLogger(__name__)


def test_connect_mongodb():
    logger.debug("health: testing mongodb connection to %s", settings.MONGO_URI)
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5_000)
    try:
        client.server_info()
    except ServerSelectionTimeoutError:
        return False, "MongoDB DB connection check failed!"
    return True, "MongoDB DB connection check succeeded!"


def test_connect_redis():
    logger.debug("health: testing Redis connection to %s", settings.REDIS_HOST)
    client = Redis(host=settings.REDIS_HOST)
    client.ping()
    return True, "Redis DB connection check succeeded!"


def test_connect_postgres():
    logger.debug("health: testing postgres connection to %s", settings.POSTGRES_HOST)
    client = PostgresqlExtDatabase(
        settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=5432,
    )
    client.connect()
    return True, "Postgres db connection check succeeded!"


def test_connect_influxdb():
    if not settings.INFLUXDB_HOST:
        return True, "skipped InfluxDB db connection test (INFLUXDB_HOST is empty)!"
    logger.debug("health: testing InfluxDB connection to %s", settings.INFLUXDB_HOST)
    client = InfluxDBClient(
        url=f"http://{settings.INFLUXDB_HOST}:{settings.INFLUXDB_PORT}",
        token=settings.INFLUXDB_AUTH_TOKEN,
        org=settings.INFLUXDB_ORG,
    )
    if not client.ping():
        return False, "InfluxDB connection check failed!"
    return True, "InfluxDB db connection check succeedeed!"


def test_connect_robotoff_api() -> tuple[bool, str]:
    logger.debug("health: testing robotoff API status")

    try:
        resp = requests.get(
            f"{settings.BaseURLProvider.robotoff()}/api/v1/status", timeout=10
        )
    except (RequestConnectionError, SSLError, Timeout) as e:
        return False, f"Robotoff API status call failed: {e}"

    if resp.status_code != 200:
        return (
            False,
            f"Robotoff API status call failed (status code {resp.status_code})",
        )

    try:
        status = resp.json().get("status")
    except JSONDecodeError as e:
        return False, f"Robotoff API status call failed: {e}"

    if status != "running":
        raise RuntimeError(f"invalid API status: {status}")

    return True, "Robotoff API status call succeeded!"


def test_connect_elasticsearch():
    logger.debug("health: testing Elasticsearch status")
    if get_es_client().ping():
        return True, "Elasticsearch connection check succeeded!"
    return False, "Elasticsearch connection check failed!"


health.add_check(test_connect_mongodb)
health.add_check(test_connect_postgres)
health.add_check(test_connect_influxdb)
health.add_check(test_connect_redis)
health.add_check(test_connect_robotoff_api)
health.add_check(test_connect_elasticsearch)
