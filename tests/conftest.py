"""Database tests tools
"""
import pytest

from robotoff import models


@pytest.fixture(scope="session")
def peewee_db_create():
    with models.db as db:
        with db.atomic():
            db.create_tables(models.MODELS, safe=True)
        print("DEBUG: models created ", db.get_tables())
    # create new connection, to avoid schema not being commited if first test fails
    models.db.close()
    models.db.connect(reuse_if_open=False)
    yield models.db


@pytest.fixture()
def peewee_db(peewee_db_create):
    yield models.db
    # issue a rollback to cope with cases of failures
    # to avoid reusing same transaction next time
    if not models.db.is_closed():
        models.db.rollback()
