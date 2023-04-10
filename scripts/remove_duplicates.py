from peewee import fn

from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
from robotoff.types import ServerType

SERVER_TYPE = ServerType.off


with db.connection_context():
    with db.atomic():
        counts = {
            item["source_image"]: item["count"]
            for item in ImageModel.select(
                ImageModel.source_image,
                fn.COUNT(ImageModel.id).alias("count"),
            )
            .where(ImageModel.server_type == SERVER_TYPE.name)
            .group_by(ImageModel.source_image)
            .having(fn.COUNT(ImageModel.id) > 1)
            .dicts()
            .iterator()
        }

print(f"duplicated groups: {len(counts)}")

with db.connection_context():
    for source_image in counts.keys():
        with db.atomic():
            image_ids = sorted(
                set(
                    item[0]
                    for item in ImageModel.select(ImageModel.id)
                    .where(
                        ImageModel.source_image == source_image,
                        ImageModel.server_type == SERVER_TYPE.name,
                    )
                    .tuples()
                )
            )
            print(f"Image {source_image}, image IDs: {image_ids}")

            if len(image_ids) <= 1:
                continue
            image_ids_to_delete = image_ids[1:]
            image_prediction_ids_to_delete = list(
                item[0]
                for item in ImagePrediction.select(ImagePrediction.id)
                .where(ImagePrediction.image_id.in_(image_ids_to_delete))
                .tuples()
            )
            logo_annotation_ids_to_delete = list(
                item[0]
                for item in LogoAnnotation.select(LogoAnnotation.id)
                .where(
                    LogoAnnotation.image_prediction_id.in_(
                        image_prediction_ids_to_delete
                    )
                )
                .tuples()
            )
            # print(f"image IDs to delete: {image_ids_to_delete}")
            # print(f"image prediction IDs to delete: {image_prediction_ids_to_delete}")
            # print(f"logo annotation IDs to delete: {logo_annotation_ids_to_delete}")

            if logo_annotation_ids_to_delete:
                LogoAnnotation.delete().where(
                    LogoAnnotation.id.in_(logo_annotation_ids_to_delete)
                ).execute()

            if image_prediction_ids_to_delete:
                ImagePrediction.delete().where(
                    ImagePrediction.id.in_(image_prediction_ids_to_delete)
                ).execute()

            if image_ids_to_delete:
                ImageModel.delete().where(
                    ImageModel.id.in_(image_ids_to_delete)
                ).execute()
