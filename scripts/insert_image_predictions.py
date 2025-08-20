import datetime
import pathlib

import tqdm

from robotoff import settings
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
from robotoff.off import generate_image_path
from robotoff.types import ProductIdentifier, ServerType
from robotoff.utils import get_logger, jsonl_iter

logger = get_logger()


DATA_PATH = settings.DATASET_DIR / "logos-paperspace.jsonl.gz"
MODEL_NAME = "universal_logo_detector"
MODEL_VERSION = "tf-universal-logo-detector-1.0"
TYPE = "object_detection"
SERVER_TYPE = ServerType.off


def get_seen_set(server_type: ServerType) -> set[tuple[str, str]]:
    seen_set: set[tuple[str, str]] = set()
    for prediction in (
        ImagePrediction.select(ImagePrediction.model_name, ImageModel.source_image)
        .join(ImageModel)
        .where(ImageModel.server_type == server_type.name)
        .iterator()
    ):
        seen_set.add((prediction.model_name, prediction.image.source_image))

    return seen_set


def insert_batch(
    data_path: pathlib.Path,
    model_name: str,
    model_version: str,
    server_type: ServerType,
) -> int:
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    logger.info("Loading seen set...")
    seen_set = get_seen_set(server_type)
    logger.info("Seen set loaded")
    inserted = 0

    for item in tqdm.tqdm(jsonl_iter(data_path)):
        barcode = item["barcode"]
        source_image = generate_image_path(
            ProductIdentifier(barcode, server_type), image_id=item["image_id"]
        )
        key = (model_name, source_image)

        if key in seen_set:
            continue

        image_instance = ImageModel.get_or_none(
            source_image=source_image, server_type=server_type.name
        )

        if image_instance is None:
            logger.warning("Unknown image in DB: %s", source_image)
            continue

        results = [r for r in item["result"] if r["score"] > 0.1]
        data = {"objects": results}
        max_confidence = max((r["score"] for r in results), default=None)

        inserted += 1
        image_prediction = ImagePrediction.create(
            type=TYPE,
            image=image_instance,
            timestamp=timestamp,
            model_name=model_name,
            model_version=model_version,
            data=data,
            max_confidence=max_confidence,
        )
        for i, item in enumerate(results):
            if item["score"] >= 0.5:
                LogoAnnotation.create(
                    image_prediction=image_prediction,
                    index=i,
                    score=item["score"],
                    bounding_box=item["bounding_box"],
                    barcode=image_instance.barcode,
                    source_image=image_instance.source_image,
                    server_type=server_type.name,
                )
        seen_set.add(key)

    return inserted


def main():
    logger.info("Starting image prediction import...")

    with db:
        inserted = insert_batch(DATA_PATH, MODEL_NAME, MODEL_VERSION, SERVER_TYPE)

    logger.info("%s image predictions inserted", inserted)


if __name__ == "__main__":
    main()
