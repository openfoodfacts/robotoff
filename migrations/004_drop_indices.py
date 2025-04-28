"""Peewee migrations -- 004_drop_logo_annotation_nearest_neighbors_index.py."""

import peewee as pw
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Drop unused indices:
    - logo_annotation_nearest_neighbors (8447 MB in prod)
    - image_prediction_data (unused, 3286 MB in prod)
    - product_insight_data (almost unused, 3047 MB in prod)
    - product_insight_predictor_version (unused, 517 MB in prod)
    - logo_annotation_bounding_box (unused, 1633 MB in prod)
    - image_prediction_max_confidence (useless, 280 MB in prod)
    - image_width (unused, 324 MB in prod)
    - image_height (unused, 310 MB in prod)

    The `logo_annotation_nearest_neighbors` index currently (as of 2024-07-11)
    takes 8447 MB of space in production, just so that we can once in a while
    get logo annotations without nearest neighbors (nearest_neighbors is NULL).
    """
    # The name of the index may change depending on how it was created
    migrator.sql("DROP INDEX IF EXISTS logo_annotation_nearest_neighbors")
    migrator.sql("DROP INDEX IF EXISTS logoannotation_nearest_neighbors")

    migrator.sql("DROP INDEX IF EXISTS image_prediction_data")
    migrator.sql("DROP INDEX IF EXISTS imageprediction_data")

    migrator.sql("DROP INDEX IF EXISTS logo_annotation_bounding_box")
    migrator.sql("DROP INDEX IF EXISTS logoannotation_bounding_box")

    migrator.sql("DROP INDEX IF EXISTS product_insight_data")
    migrator.sql("DROP INDEX IF EXISTS productinsight_data")

    migrator.sql("DROP INDEX IF EXISTS image_prediction_max_confidence")
    migrator.sql("DROP INDEX IF EXISTS imageprediction_max_confidence")

    migrator.sql("DROP INDEX IF EXISTS image_width")
    migrator.sql("DROP INDEX IF EXISTS imagemodel_width")

    migrator.sql("DROP INDEX IF EXISTS image_height")
    migrator.sql("DROP INDEX IF EXISTS imagemodel_height")

    migrator.sql("DROP INDEX IF EXISTS product_insight_predictor_version")
    migrator.sql("DROP INDEX IF EXISTS productinsight_predictor_version")


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """These indices are too long to build using a migration script, rollback
    should be done manually."""
    pass
