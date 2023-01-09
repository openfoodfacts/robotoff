import datetime
import pathlib

import tqdm
from more_itertools import chunked

from robotoff.logos import filter_logos
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
from robotoff.off import generate_image_path
from robotoff.utils import get_logger, jsonl_iter

logger = get_logger(__name__)


TYPE = "object_detection"


def get_seen_set() -> set[tuple[str, str]]:
    seen_set: set[tuple[str, str]] = set()
    for item in (
        ImagePrediction.select(ImagePrediction.model_name, ImageModel.source_image)
        .join(ImageModel)
        .tuples()
        .iterator()
    ):
        seen_set.add(item)
    return seen_set


def import_logos(
    data_path: pathlib.Path, model_name: str, model_version: str, batch_size: int
) -> int:
    logger.info("Loading seen set...")
    seen_set = get_seen_set()
    logger.info("Seen set loaded")
    inserted = 0

    for batch in chunked(tqdm.tqdm(jsonl_iter(data_path)), batch_size):
        with db.atomic():
            timestamp = datetime.datetime.utcnow()
            for item in batch:
                barcode = item["barcode"]
                source_image = generate_image_path(
                    barcode=barcode, image_id=item["image_id"]
                )
                key = (model_name, source_image)

                if key in seen_set:
                    continue

                image_instance = ImageModel.get_or_none(source_image=source_image)

                if image_instance is None:
                    logger.info("Unknown image in DB: %s", source_image)
                    continue

                results = [r for r in item["result"] if r["score"] > 0.1]
                data = {"objects": results}
                max_confidence = max([r["score"] for r in results], default=None)

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
                for i, item in filter_logos(
                    image_prediction.data["objects"],
                    score_threshold=0.5,
                    iou_threshold=0.95,
                ):
                    LogoAnnotation.create(
                        image_prediction=image_prediction,
                        index=i,
                        score=item["score"],
                        bounding_box=item["bounding_box"],
                        barcode=image_instance.barcode,
                        source_image=image_instance.source_image,
                    )
                seen_set.add(key)

    return inserted
