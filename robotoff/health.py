import requests
from healthcheck import HealthCheck
from influxdb_client import InfluxDBClient
from playhouse.postgres_ext import PostgresqlExtDatabase
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from redis import Redis

from robotoff import settings
from robotoff.utils import get_logger

health = HealthCheck()

logger = get_logger(__name__)


def test_connect_mongodb():
    logger.debug("health: testing mongodb connection to %s", settings.MONGO_URI)
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5_000)
    try:
        client.server_info()
    except ServerSelectionTimeoutError:
        return False, "MongoDB DB connection failed!"
    return True, "MongoDB DB connection succeeded!"


def test_connect_redis():
    logger.debug("health: testing Redis connection to %s", settings.REDIS_HOST)
    client = Redis(host=settings.REDIS_HOST)
    client.ping()
    return True, "Redis DB connection success!"


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
    return True, "Postgres db connection success !"


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
        return False, "InfluxDB connection failed!"
    return True, "InfluxDB db connection success!"


def test_connect_robotoff_api():
    logger.debug("health: testing robotoff API status")
    resp = requests.get(f"{settings.BaseURLProvider().robotoff().get()}/api/v1/status")
    return resp.json()["status"] == "running", "Robotoff API connection success !"


def test_connect_ann():
    logger.debug("health: testing robotoff ann status")
    resp = requests.get(
        f"{settings.BaseURLProvider().robotoff().get()}/api/v1/ann/?count=1"
    )
    return "count" in resp.json(), "ANN API connection success !"


health.add_check(test_connect_mongodb)
health.add_check(test_connect_postgres)
health.add_check(test_connect_influxdb)
health.add_check(test_connect_redis)
health.add_check(test_connect_robotoff_api)
health.add_check(test_connect_ann)
