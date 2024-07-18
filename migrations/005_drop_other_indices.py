import peewee as pw
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Drop unused indices:

    - prediction_data: 6242 MB in prod
    - prediction_source_image: 1795 MB in prod
    - product_insight_bounding_box: 188 MB in prod
    - product_insight_confidence: 332 MB in prod
    - image_prediction_model_version: 533 MB in prod
    - product_insight_username: 661 MB in prod
    """
    migrator.sql("DROP INDEX IF EXISTS prediction_data")
    migrator.sql("DROP INDEX IF EXISTS prediction_source_image")

    migrator.sql("DROP INDEX IF EXISTS logo_confidence_threshold_type")
    migrator.sql("DROP INDEX IF EXISTS logoconfidencethreshold_type")

    migrator.sql("DROP INDEX IF EXISTS logo_confidence_threshold_value")
    migrator.sql("DROP INDEX IF EXISTS logoconfidencethreshold_value")

    migrator.sql("DROP INDEX IF EXISTS product_insight_bounding_box")
    migrator.sql("DROP INDEX IF EXISTS productinsight_bounding_box")

    migrator.sql("DROP INDEX IF EXISTS product_insight_confidence")
    migrator.sql("DROP INDEX IF EXISTS productinsight_confidence")

    migrator.sql("DROP INDEX IF EXISTS image_prediction_model_version")
    migrator.sql("DROP INDEX IF EXISTS imagepredictionmodel_version")

    migrator.sql("DROP INDEX IF EXISTS product_insight_username")
    migrator.sql("DROP INDEX IF EXISTS productinsight_username")


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """These indices are too long to build using a migration script, rollback
    should be done manually."""
    pass
