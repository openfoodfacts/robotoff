import peewee as pw
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    migrator.add_fields(
        "logo_annotation",
        server_type=pw.CharField(
            null=True,
            max_length=10,
            help_text="project associated with the logo annotation, "
            "one of 'off', 'obf', 'opff', 'opf', 'off-pro'",
            index=False,
        ),
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_fields("logo_annotation", "server_type")
