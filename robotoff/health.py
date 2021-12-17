import requests
from healthcheck import HealthCheck
from influxdb import InfluxDBClient
from playhouse.postgres_ext import PostgresqlExtDatabase
from pymongo import MongoClient

from robotoff import settings
from robotoff.utils import get_logger

health = HealthCheck()

logger = get_logger(__name__)


def test_connect_mongodb():
    client = MongoClient(settings.MONGO_URI)
    client.server_info()
    return True, "MongoDB db connection success !"


def test_connect_postgres():
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
    client = InfluxDBClient(
        settings.INFLUXDB_HOST,
        settings.INFLUXDB_PORT,
        settings.INFLUXDB_USERNAME,
        settings.INFLUXDB_PASSWORD,
        settings.INFLUXDB_DB_NAME,
    )
    client.get_list_users()
    return True, "InfluxDB db connection success !"


def test_connect_ann():
    resp = requests.get(
        f"{settings.BaseURLProvider().robotoff().get()}/ann/api/v1/status"
    )
    return resp.json()["status"] == "running", "ANN API connection success !"


health.add_check(test_connect_mongodb)
health.add_check(test_connect_postgres)
health.add_check(test_connect_influxdb)
health.add_check(test_connect_ann)
