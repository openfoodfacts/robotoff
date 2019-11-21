from typing import Iterable, Dict

import peewee
from playhouse.postgres_ext import (PostgresqlExtDatabase,
                                    BinaryJSONField)

from robotoff import settings
from robotoff.utils.types import JSONType

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


class ProductInsight(BaseModel):
    id = peewee.UUIDField(primary_key=True)
    barcode = peewee.CharField(max_length=100, null=False, index=True)
    type = peewee.CharField(max_length=256)
    data = BinaryJSONField(index=True)
    timestamp = peewee.DateTimeField(null=True)
    completed_at = peewee.DateTimeField(null=True)
    annotation = peewee.IntegerField(null=True)
    countries = BinaryJSONField(null=True, index=True)
    brands = BinaryJSONField(null=True, index=True)
    process_after = peewee.DateTimeField(null=True)
    value_tag = peewee.TextField(null=True, index=True)
    source_image = peewee.TextField(null=True, index=True)
    automatic_processing = peewee.BooleanField(default=False, index=True)

    def serialize(self, full: bool = False) -> JSONType:
        if full:
            return {
                'id': str(self.id),
                'barcode': self.barcode,
                'type': self.type,
                'data': self.data,
                'timestamp': self.timestamp.isoformat() if self.timestamp else None,
                'completed_at': self.completed_at.isoformat() if self.completed_at else None,
                'annotation': self.annotation,
                'countries': self.countries,
                'brands': self.brands,
                'process_after': self.process_after.isoformat() if self.process_after else None,
                'value_tag': self.value_tag,
                'source_image': self.source_image,
                'automatic_processing': self.automatic_processing,
            }
        else:
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


MODELS = [ProductInsight, ProductIngredient]
