"""Peewee migrations -- 008_add_insight_lc.py."""

import peewee as pw
import playhouse.postgres_ext as pw_pext
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.add_fields(
        "ProductInsight",
        lc=pw_pext.ArrayField(
            pw.CharField,
            null=True,
            help_text="language codes of the insight, if any, e.g. 'en', 'fr', 'de'",
            index=True,
        ),
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.remove_fields("ProductInsight", "lc")
