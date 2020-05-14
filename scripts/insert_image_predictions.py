import datetime
import pathlib
import uuid
from typing import Set, Tuple

from robotoff.models import db, ImagePrediction, batch_insert
from robotoff.off import get_server_type, generate_image_path
from robotoff.utils import jsonl_iter, get_logger
from robotoff import settings
import tqdm

logger = get_logger()


DATA_PATH = settings.PROJECT_DIR / "output.jsonl.gz"
MODEL_NAME = "universal-logo-detector"
MODEL_VERSION = "tf-universal-logo-detector-1.0"
TYPE = "object_detection"


def get_seen_set() -> Set[Tuple[str, str]]:
    seen_set: Set[Tuple[str, str]] = set()
    for prediction in ImagePrediction.select(
        ImagePrediction.model_name, ImagePrediction.source_image
    ).iterator():
        seen_set.add((prediction.model_name, prediction.source_image))

    return seen_set


def iter_insert(data_path: pathlib.Path, model_name: str, model_version: str):
    timestamp = datetime.datetime.utcnow()
    server_domain = settings.OFF_SERVER_DOMAIN
    server_type: str = get_server_type(server_domain).name
    logger.info("Loading seen set...")
    seen_set = get_seen_set()
    logger.info("Seen set loaded")

    for item in jsonl_iter(data_path):
        source_image = generate_image_path(item["barcode"], item["image_id"])
        key = (model_name, source_image)

        if key in seen_set:
            continue

        results = item["result"]
        data = {"objects": results}
        max_confidence = max([r["score"] for r in results], default=None)

        yield {
            "id": str(uuid.uuid4()),
            "type": TYPE,
            "barcode": item["barcode"],
            "timestamp": timestamp,
            "server_domain": server_domain,
            "server_type": server_type,
            "source_image": source_image,
            "model_name": model_name,
            "model_version": model_version,
            "data": data,
            "max_confidence": max_confidence,
        }
        seen_set.add(key)


logger.info("Starting image prediction import...")
inserts = tqdm.tqdm(iter_insert(DATA_PATH, MODEL_NAME, MODEL_VERSION))

with db:
    with db.atomic():
        inserted = batch_insert(ImagePrediction, inserts)

logger.info("{} image predictions inserted".format(inserted))
