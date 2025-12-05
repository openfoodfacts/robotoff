"""Peewee migrations -- 009_add_insight_with_image.py."""

import peewee as pw
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.add_fields(
        "ProductInsight",
        with_image=pw.BooleanField(
            null=True,
            help_text="Whether we have an image to display to illustrate the insight",
            index=True,
        ),
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.remove_fields("ProductInsight", "with_image")
