import pytest
import requests
from influxdb import InfluxDBClient
from playhouse.postgres_ext import PostgresqlExtDatabase
from pymongo import MongoClient

from robotoff import settings


def test_connect_mongodb():
    client = MongoClient(settings.MONGO_URI)
    client.server_info()


def test_connect_postgres():
    client = PostgresqlExtDatabase(
        settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=5432,
    )
    client.connect()


def test_connect_influxdb():
    client = InfluxDBClient(
        settings.INFLUXDB_HOST,
        settings.INFLUXDB_PORT,
        settings.INFLUXDB_USERNAME,
        settings.INFLUXDB_PASSWORD,
        settings.INFLUXDB_DB_NAME,
    )
    client.get_list_users()


def test_connect_ann():
    resp = requests.get(
        f"{settings.BaseURLProvider().robotoff().get()}/ann/api/v1/status"
    )
    assert resp.json()["status"] == "running"


# TODO: Automate model health checks
# def test_connect_tfserving():
#     req = requests.get(f'https://{settings.TF_SERVING_BASE_URL}/v1/models/{model}/labels/{label}')
#     assert req.json()['model_version_status'] == 1
