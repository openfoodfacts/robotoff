"""Peewee migrations -- 001_initial.py."""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class ProductInsight(pw.Model):
        id = pw.UUIDField(primary_key=True)
        barcode = pw.CharField(index=True, max_length=100)
        type = pw.CharField(index=True, max_length=256)
        data = pw_pext.BinaryJSONField(index=True)
        timestamp = pw.DateTimeField(index=True, null=True)
        completed_at = pw.DateTimeField(null=True)
        annotation = pw.IntegerField(index=True, null=True)
        annotated_result = pw.IntegerField(null=True)
        n_votes = pw.IntegerField(index=True)
        username = pw.TextField(index=True, null=True)
        countries = pw_pext.BinaryJSONField(index=True, null=True)
        brands = pw_pext.BinaryJSONField(index=True, null=True)
        process_after = pw.DateTimeField(null=True)
        value_tag = pw.TextField(index=True, null=True)
        value = pw.TextField(index=True, null=True)
        source_image = pw.TextField(index=True, null=True)
        automatic_processing = pw.BooleanField(default=False, index=True)
        server_type = pw.CharField(index=True, max_length=10, null=True)
        unique_scans_n = pw.IntegerField(default=0, index=True)
        reserved_barcode = pw.BooleanField(default=False, index=True)
        predictor = pw.CharField(index=True, max_length=100, null=True)
        predictor_version = pw.CharField(index=True, max_length=100, null=True)
        campaign = pw_pext.BinaryJSONField(index=True, null=True)
        confidence = pw.FloatField(index=True, null=True)

        class Meta:
            table_name = "product_insight"

    @migrator.create_model
    class AnnotationVote(pw.Model):
        id = pw.UUIDField(primary_key=True)
        insight_id = pw.ForeignKeyField(
            column_name="insight_id",
            field="id",
            model=migrator.orm["product_insight"],
            on_delete="CASCADE",
        )
        username = pw.TextField(index=True, null=True)
        value = pw.IntegerField()
        device_id = pw.TextField(index=True)
        timestamp = pw.DateTimeField()

        class Meta:
            table_name = "annotation_vote"

    @migrator.create_model
    class BaseModel(pw.Model):
        id = pw.AutoField()

        class Meta:
            table_name = "base_model"

    @migrator.create_model
    class ImageModel(pw.Model):
        id = pw.AutoField()
        barcode = pw.CharField(index=True, max_length=100)
        uploaded_at = pw.DateTimeField(index=True, null=True)
        image_id = pw.CharField(index=True, max_length=50)
        source_image = pw.TextField(index=True)
        width = pw.IntegerField(index=True)
        height = pw.IntegerField(index=True)
        deleted = pw.BooleanField(default=False, index=True)
        server_type = pw.CharField(index=True, max_length=10, null=True)
        fingerprint = pw.BigIntegerField(index=True, null=True)

        class Meta:
            table_name = "image"

    @migrator.create_model
    class ImageEmbedding(pw.Model):
        image = pw.ForeignKeyField(
            column_name="image_id",
            field="id",
            model=migrator.orm["image"],
            on_delete="CASCADE",
            primary_key=True,
        )
        embedding = pw.BlobField()

        class Meta:
            table_name = "image_embedding"
            schema = "embedding"

    @migrator.create_model
    class ImagePrediction(pw.Model):
        id = pw.AutoField()
        type = pw.CharField(max_length=256)
        model_name = pw.CharField(index=True, max_length=100)
        model_version = pw.CharField(index=True, max_length=256)
        data = pw_pext.BinaryJSONField(index=True)
        timestamp = pw.DateTimeField(null=True)
        image = pw.ForeignKeyField(
            column_name="image_id", field="id", model=migrator.orm["image"]
        )
        max_confidence = pw.FloatField(index=True, null=True)

        class Meta:
            table_name = "image_prediction"

    @migrator.create_model
    class LogoAnnotation(pw.Model):
        id = pw.AutoField()
        image_prediction = pw.ForeignKeyField(
            column_name="image_prediction_id",
            field="id",
            model=migrator.orm["image_prediction"],
        )
        index = pw.IntegerField()
        bounding_box = pw_pext.BinaryJSONField(index=True)
        score = pw.FloatField()
        annotation_value = pw.CharField(index=True, max_length=255, null=True)
        annotation_value_tag = pw.CharField(index=True, max_length=255, null=True)
        taxonomy_value = pw.CharField(index=True, max_length=255, null=True)
        annotation_type = pw.CharField(index=True, max_length=255, null=True)
        username = pw.TextField(index=True, null=True)
        completed_at = pw.DateTimeField(index=True, null=True)
        nearest_neighbors = pw_pext.BinaryJSONField(index=True, null=True)
        barcode = pw.CharField(index=True, max_length=100, null=True)
        source_image = pw.TextField(index=True, null=True)

        class Meta:
            table_name = "logo_annotation"

    @migrator.create_model
    class LogoConfidenceThreshold(pw.Model):
        id = pw.AutoField()
        type = pw.CharField(index=True, max_length=255, null=True)
        value = pw.CharField(index=True, max_length=255, null=True)
        threshold = pw.FloatField()

        class Meta:
            table_name = "logo_confidence_threshold"

    @migrator.create_model
    class LogoEmbedding(pw.Model):
        logo = pw.ForeignKeyField(
            column_name="logo_id",
            field="id",
            model=migrator.orm["logo_annotation"],
            on_delete="CASCADE",
            primary_key=True,
        )
        embedding = pw.BlobField()

        class Meta:
            table_name = "logo_embedding"
            schema = "embedding"

    @migrator.create_model
    class Prediction(pw.Model):
        id = pw.AutoField()
        barcode = pw.CharField(index=True, max_length=100)
        type = pw.CharField(index=True, max_length=256)
        data = pw_pext.BinaryJSONField(index=True)
        timestamp = pw.DateTimeField(index=True)
        value_tag = pw.TextField(null=True)
        value = pw.TextField(null=True)
        source_image = pw.TextField(index=True, null=True)
        automatic_processing = pw.BooleanField(null=True)
        predictor = pw.CharField(max_length=100, null=True)
        predictor_version = pw.CharField(max_length=100, null=True)
        confidence = pw.FloatField(null=True)
        server_type = pw.CharField(default="off", index=True, max_length=10)

        class Meta:
            table_name = "prediction"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_model("prediction")

    migrator.remove_model("logo_embedding")

    migrator.remove_model("logo_confidence_threshold")

    migrator.remove_model("logo_annotation")

    migrator.remove_model("image_prediction")

    migrator.remove_model("image")

    migrator.remove_model("image_embedding")

    migrator.remove_model("base_model")

    migrator.remove_model("annotation_vote")

    migrator.remove_model("product_insight")
