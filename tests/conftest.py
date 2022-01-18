"""Database tests tools
"""
import pytest

from robotoff import models


@pytest.fixture(scope="session")
def peewee_db():
    with models.db:
        models.db.create_tables(models.MODELS, safe=True)
