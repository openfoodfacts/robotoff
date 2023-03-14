"""Database tests tools
"""
import pytest

from robotoff import models, settings
from robotoff.redis import Lock
from robotoff.taxonomy import Taxonomy


@pytest.fixture(scope="session", autouse=True)
def disable_redis_lock():
    previous_value = Lock._enabled
    Lock._enabled = False
    yield
    Lock._enabled = previous_value


@pytest.fixture(scope="session")
def peewee_db_create():
    models.db.close()  # insure creating a new connection
    with models.db as db:
        models.db.execute_sql("CREATE SCHEMA IF NOT EXISTS embedding;")
        db.create_tables(models.MODELS, safe=True)
        print("DEBUG: models created ", db.get_tables())
    yield models.db


@pytest.fixture()
def peewee_db(peewee_db_create):
    yield models.db
    # issue a rollback to cope with cases of failures
    # to avoid reusing same transaction next time
    if not models.db.is_closed():
        models.db.rollback()
        models.db.close()


@pytest.fixture(scope="session")
def category_taxonomy():
    return Taxonomy.from_json(settings.TAXONOMY_PATHS["category"])
