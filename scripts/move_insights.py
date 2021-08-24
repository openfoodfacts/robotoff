import peewee
import tqdm
from playhouse.postgres_ext import BinaryJSONField

from robotoff.insights._enum import InsightType
from robotoff.models import BaseModel, ProductInsight


class LatentProductInsight(BaseModel):
    id = peewee.UUIDField(primary_key=True)
    barcode = peewee.CharField(max_length=100, null=False, index=True)
    type = peewee.CharField(max_length=256)
    data = BinaryJSONField(index=True)
    timestamp = peewee.DateTimeField(null=True)
    value_tag = peewee.TextField(null=True, index=True)
    value = peewee.TextField(null=True, index=True)
    source_image = peewee.TextField(null=True, index=True)
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


insight_types = [
    InsightType.image_lang.name,
    InsightType.image_orientation.name,
    InsightType.nutrient_mention.name,
    InsightType.nutrient.name,
]

moved = 0

for insight in tqdm.tqdm(
    LatentProductInsight.select()
    .where(LatentProductInsight.type.in_(insight_types))
    .iterator()
):
    ProductInsight.create_from_latent(insight)
    moved += 1


print("{} insights moved".format(moved))
