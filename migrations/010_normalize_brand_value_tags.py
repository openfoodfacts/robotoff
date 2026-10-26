"""Store brand prediction and insight tags in their canonical xx: form."""

import peewee as pw
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    # Update in place to preserve insight IDs, annotations and their votes.
    # Empty values and explicitly namespaced tags are intentionally untouched.
    for table in ("prediction", "product_insight"):
        migrator.sql(
            f"UPDATE {table} SET value_tag = 'xx:' || value_tag "
            "WHERE type = 'brand' AND value_tag <> '' "
            "AND position(':' in value_tag) = 0"
        )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    # The original spelling cannot be recovered without a backup. Retain
    # canonical tags instead of stripping prefixes from pre-existing data.
    pass
