"""Peewee migrations -- 002_add_bounding_box.py."""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    migrator.add_fields(
        "product_insight", bounding_box=pw_pext.BinaryJSONField(index=True, null=True)
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_fields("product_insight", "bounding_box")
