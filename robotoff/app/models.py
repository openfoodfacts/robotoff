import peewee
from playhouse.postgres_ext import (PostgresqlExtDatabase,
                                    BinaryJSONField)

from robotoff import settings

db = PostgresqlExtDatabase(settings.DB_NAME,
                           user=settings.DB_USER,
                           password=settings.DB_PASSWORD,
                           host=settings.DB_HOST, port=5432)


class CategorizationTask(peewee.Model):
    id = peewee.UUIDField(primary_key=True)
    product_id = peewee.CharField(max_length=100, null=False)
    predicted_category = peewee.TextField(null=False)
    confidence = peewee.FloatField(null=True)
    last_updated_at = peewee.TextField(null=False)
    completed_at = peewee.DateTimeField(null=True)
    annotation = peewee.IntegerField(null=True)
    outdated = peewee.BooleanField(default=False)
    category_depth = peewee.IntegerField(null=True, index=True)
    campaign = peewee.TextField(null=True, index=True)
    countries = BinaryJSONField(null=True, index=True)

    class Meta:
        database = db
        table_name = "categorization_task"


class ProductInsight(peewee.Model):
    id = peewee.UUIDField(primary_key=True)
    barcode = peewee.CharField(max_length=100, null=False, index=True)
    type = peewee.CharField(max_length=256)
    data = BinaryJSONField(index=True)
    timestamp = peewee.DateTimeField(null=True)
    completed_at = peewee.DateTimeField(null=True)
    annotation = peewee.IntegerField(null=True)
    outdated = peewee.BooleanField(default=False)
    countries = BinaryJSONField(null=True, index=True)

    class Meta:
        database = db
        table_name = "product_insight"


MODELS = [CategorizationTask, ProductInsight]
