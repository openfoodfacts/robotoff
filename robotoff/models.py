# This package describes the Postgres tables Robotoff is writing to.
from typing import Dict, Iterable

import peewee
from playhouse.postgres_ext import BinaryJSONField, PostgresqlExtDatabase
from playhouse.shortcuts import model_to_dict

from robotoff import settings
from robotoff.utils.types import JSONType

db = PostgresqlExtDatabase(
    settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=5432,
)


def batch_insert(model_cls, data: Iterable[Dict], batch_size=100) -> int:
    rows = 0
    inserts = []

    for item in data:
        inserts.append(item)
        rows += 1

        if rows % batch_size == 0:
            model_cls.insert_many(inserts).execute()
            inserts = []

    if inserts:
        model_cls.insert_many(inserts).execute()

    return rows


class BaseModel(peewee.Model):
    class Meta:
        database = db
        legacy_table_names = False

    def to_dict(self, **kwargs):
        return model_to_dict(self, **kwargs)


class ProductInsight(BaseModel):
    id = peewee.UUIDField(primary_key=True)
    # Barcode represents the barcode of the product for which the insight was generated.
    barcode = peewee.CharField(max_length=100, null=False, index=True)

    # Type represents the insight type - must match one of the types in robotoff.insights._enum.
    type = peewee.CharField(max_length=256)

    # Contains some additional data based on the type of the insight from above.
    # NOTE: there is no 1:1 mapping between the type and the JSON format provided here, for example for
    # type==label, the data here could be:
    # {"logo_id":X,"confidence":Y}, or
    # {"text":X,"notify":Y}
    data = BinaryJSONField(index=True)

    # Timestamp is the timestamp of when this insight was imported into the DB.
    timestamp = peewee.DateTimeField(null=True, index=True)

    # Stores the timestamp of when this insight was annotated.
    completed_at = peewee.DateTimeField(null=True)

    # The annotation of the given insight. Three possible values are possible:
    #  -1 = rejected
    # 0 = pending
    # 1 = validated
    annotation = peewee.IntegerField(null=True, index=True)

    # Latent described whether the annotation is applied automatically:
    # latent==true - the annotation is NOT applied automatically.
    latent = peewee.BooleanField(null=False, index=True, default=False)

    
    countries = BinaryJSONField(null=True, index=True)
    brands = BinaryJSONField(null=True, index=True)
    process_after = peewee.DateTimeField(null=True)
    value_tag = peewee.TextField(null=True, index=True)
    value = peewee.TextField(null=True, index=True)
    source_image = peewee.TextField(null=True, index=True)
    automatic_processing = peewee.BooleanField(default=False, index=True)
    server_domain = peewee.TextField(
        null=True, help_text="server domain linked to the insight", index=True
    )
    server_type = peewee.CharField(
        null=True,
        max_length=10,
        help_text="project associated with the server_domain, "
        "one of 'off', 'obf', 'opff', 'opf'",
        index=True,
    )
    unique_scans_n = peewee.IntegerField(default=0, index=True)
    reserved_barcode = peewee.BooleanField(default=False, index=True)
    predictor = peewee.CharField(max_length=100, null=True, index=True)
    username = peewee.TextField(index=True)

    def serialize(self) -> JSONType:
        return {
            "id": str(self.id),
            "type": self.type,
            "barcode": self.barcode,
            "countries": self.countries,
            "source_image": self.source_image,
            **self.data,
        }

    @classmethod
    def create_from_latent(cls, latent_insight: "ProductInsight", **kwargs):
        updated_values = {**latent_insight.__data__, **kwargs}
        return cls.create(**updated_values)


class ImageModel(BaseModel):
    barcode = peewee.CharField(max_length=100, null=False, index=True)
    uploaded_at = peewee.DateTimeField(null=True, index=True)
    image_id = peewee.CharField(max_length=50, null=False, index=True)
    source_image = peewee.TextField(null=False, index=True)
    width = peewee.IntegerField(null=False, index=True)
    height = peewee.IntegerField(null=False, index=True)
    deleted = peewee.BooleanField(null=False, index=True, default=False)
    server_domain = peewee.TextField(null=True, index=True)
    server_type = peewee.CharField(null=True, max_length=10, index=True)

    class Meta:
        table_name = "image"


class ImagePrediction(BaseModel):
    """Table to store computer vision predictions (object detection,
    image segmentation,...) made by custom models."""

    type = peewee.CharField(max_length=256)
    model_name = peewee.CharField(max_length=100, null=False, index=True)
    model_version = peewee.CharField(max_length=256, null=False, index=True)
    data = BinaryJSONField(index=True)
    timestamp = peewee.DateTimeField(null=True)
    image = peewee.ForeignKeyField(ImageModel, null=False, backref="predictions")
    max_confidence = peewee.FloatField(
        null=True,
        index=True,
        help_text="for object detection models, confidence of the highest confident"
        "object detected, null if no object was detected",
    )


class LogoAnnotation(BaseModel):
    image_prediction = peewee.ForeignKeyField(
        ImagePrediction, null=False, backref="logo_detections"
    )
    index = peewee.IntegerField(null=False, constraints=[peewee.Check("index >= 0")])
    bounding_box = BinaryJSONField(null=False)
    score = peewee.FloatField(null=False)
    annotation_value = peewee.CharField(null=True, index=True)
    annotation_value_tag = peewee.CharField(null=True, index=True)
    taxonomy_value = peewee.CharField(null=True, index=True)
    annotation_type = peewee.CharField(null=True, index=True)
    username = peewee.TextField(null=True, index=True)
    completed_at = peewee.DateTimeField(null=True, index=True)
    nearest_neighbors = BinaryJSONField(null=True)

    class Meta:
        constraints = [peewee.SQL("UNIQUE(image_prediction_id, index)")]

    def get_crop_image_url(self) -> str:
        base_url = (
            settings.OFF_IMAGE_BASE_URL + self.image_prediction.image.source_image
        )
        y_min, x_min, y_max, x_max = self.bounding_box
        base_robotoff_url = settings.BaseURLProvider().robotoff()
        return f"https://{base_robotoff_url}/api/v1/images/crop?image_url={base_url}&y_min={y_min}&x_min={x_min}&y_max={y_max}&x_max={x_max}"


class LogoConfidenceThreshold(BaseModel):
    type = peewee.CharField(null=True, index=True)
    value = peewee.CharField(null=True, index=True)
    threshold = peewee.FloatField(null=False)


MODELS = [
    ProductInsight,
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    LogoConfidenceThreshold,
]
