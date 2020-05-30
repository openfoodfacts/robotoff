import datetime
import pathlib
from typing import Set, Tuple

from robotoff.models import (
    db,
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
)
from robotoff.off import generate_image_path
from robotoff.utils import jsonl_iter, get_logger
from robotoff import settings
import tqdm

logger = get_logger()


DATA_PATH = settings.DATASET_DIR / "output.jsonl.gz"
MODEL_NAME = "universal-logo-detector"
MODEL_VERSION = "tf-universal-logo-detector-1.0"
TYPE = "object_detection"


def get_seen_set() -> Set[Tuple[str, str]]:
    seen_set: Set[Tuple[str, str]] = set()
    for prediction in (
        ImagePrediction.select(ImagePrediction.model_name, ImageModel.source_image)
        .join(ImageModel)
        .iterator()
    ):
        seen_set.add((prediction.model_name, prediction.image.source_image))

    return seen_set


def insert_batch(data_path: pathlib.Path, model_name: str, model_version: str):
    timestamp = datetime.datetime.utcnow()
    logger.info("Loading seen set...")
    seen_set = get_seen_set()
    logger.info("Seen set loaded")

    for item in tqdm.tqdm(jsonl_iter(data_path)):
        barcode = item["barcode"]
        source_image = generate_image_path(barcode=barcode, image_id=item["image_id"])
        key = (model_name, source_image)

        if key in seen_set:
            continue

        image_instance = ImageModel.get_or_none(source_image=source_image)

        if image_instance is None:
            logger.warning("Unknown image in DB: {}".format(source_image))
            continue

        results = [r for r in item["result"] if r["score"] > 0.1]
        data = {"objects": results}
        max_confidence = max([r["score"] for r in results], default=None)

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
                )
        seen_set.add(key)


logger.info("Starting image prediction import...")

with db:
    inserted = insert_batch(DATA_PATH, MODEL_NAME, MODEL_VERSION)

logger.info("{} image predictions inserted".format(inserted))
