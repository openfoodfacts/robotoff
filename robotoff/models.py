from typing import Iterable, Dict

import peewee
from playhouse.postgres_ext import (PostgresqlExtDatabase,
                                    BinaryJSONField)

from robotoff import settings

db = PostgresqlExtDatabase(settings.DB_NAME,
                           user=settings.DB_USER,
                           password=settings.DB_PASSWORD,
                           host=settings.DB_HOST, port=5432)


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


class CategorizationTask(BaseModel):
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


class ProductInsight(BaseModel):
    id = peewee.UUIDField(primary_key=True)
    barcode = peewee.CharField(max_length=100, null=False, index=True)
    type = peewee.CharField(max_length=256)
    data = BinaryJSONField(index=True)
    timestamp = peewee.DateTimeField(null=True)
    completed_at = peewee.DateTimeField(null=True)
    annotation = peewee.IntegerField(null=True)
    outdated = peewee.BooleanField(default=False)
    countries = BinaryJSONField(null=True, index=True)

    def serialize(self):
        return {
            'id': str(self.id),
            'type': self.type,
            'barcode': self.barcode,
            'countries': self.countries,
            **self.data,
        }


class ProductIngredient(BaseModel):
    barcode = peewee.CharField(max_length=100, null=False, index=True, unique=True)
    ingredients = peewee.TextField(null=False)


MODELS = [CategorizationTask, ProductInsight, ProductIngredient]
