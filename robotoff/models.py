import datetime
from typing import Iterable, Dict, Optional

import peewee
from playhouse.postgres_ext import PostgresqlExtDatabase, BinaryJSONField

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

    def serialize(self, full: bool = False) -> JSONType:
        if full:
            return {
                "id": str(self.id),
                "barcode": self.barcode,
                "type": self.type,
                "data": self.data,
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
                "completed_at": self.completed_at.isoformat()
                if self.completed_at
                else None,
                "annotation": self.annotation,
                "countries": self.countries,
                "brands": self.brands,
                "process_after": self.process_after.isoformat()
                if self.process_after
                else None,
                "value_tag": self.value_tag,
                "value": self.value,
                "source_image": self.source_image,
                "automatic_processing": self.automatic_processing,
                "server_domain": self.server_domain,
                "server_type": self.server_type,
                "unique_scans_n": self.unique_scans_n,
            }
        else:
            return {
                "id": str(self.id),
                "type": self.type,
                "barcode": self.barcode,
                "countries": self.countries,
                **self.data,
            }


class UserAnnotation(BaseModel):
    insight = peewee.ForeignKeyField(
        ProductInsight, primary_key=True, backref="user_annotation"
    )
    username = peewee.TextField(index=True)

    @property
    def annotation(self) -> Optional[int]:
        return self.insight.annotation

    @property
    def completed_at(self) -> Optional[datetime.datetime]:
        return self.insight.completed_at


class ProductIngredient(BaseModel):
    barcode = peewee.CharField(max_length=100, null=False, index=True, unique=True)
    ingredients = peewee.TextField(null=False)


MODELS = [ProductInsight, UserAnnotation, ProductIngredient]
