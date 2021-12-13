import pytest

from playhouse.postgres_ext import PostgresqlExtDatabase
from pymongo import MongoClient
from influxdb import InfluxDBClient

from robotoff import settings

@pytest.mark.integtest
def test_connect_mongodb():
    client = MongoClient(settings.MONGO_URI)
    client.server_info()

@pytest.mark.integtest
def test_connect_postgres():
    client = PostgresqlExtDatabase(
        settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=5432,
    )
    client.connect()

@pytest.mark.integtest
def test_connect_influxdb():
    client = InfluxDBClient(
        settings.INFLUXDB_HOST,
        settings.INFLUXDB_PORT,
        settings.INFLUXDB_USERNAME,
        settings.INFLUXDB_PASSWORD,
        settings.INFLUXDB_DB_NAME,
    )
    client.get_list_users()
