import peewee as pw
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.sql(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS logo_annotation_server_type ON logo_annotation (server_type)"
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.sql("DROP INDEX IF EXISTS logo_annotation_server_type")
