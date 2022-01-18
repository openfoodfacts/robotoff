import contextlib
import datetime
import json
import pathlib
import sys
from typing import Dict, Iterable, List, Optional, Set, TextIO, Union

import click
from more_itertools import chunked
from peewee import fn

from robotoff.insights import InsightType
from robotoff.insights.annotate import InsightAnnotatorFactory
from robotoff.insights.importer import AUTHORIZED_LABELS_STORE
from robotoff.insights.importer import import_insights as import_insights_
from robotoff.models import ProductInsight, db
from robotoff.off import get_product
from robotoff.prediction.ocr import (
    OCRResult,
    extract_predictions,
    get_barcode_from_path,
    ocr_iter,
)
from robotoff.prediction.types import PredictionType, ProductPredictions
from robotoff.products import get_product_store
from robotoff.utils import get_logger, jsonl_iter

logger = get_logger(__name__)


def run_from_ocr_archive(
    input_: Union[str, TextIO],
    prediction_type: PredictionType,
    output: Optional[pathlib.Path] = None,
    keep_empty: bool = False,
):
    predictions = generate_from_ocr_archive(input_, prediction_type, keep_empty)

    if output is not None:
        output_f = output.open("w")
    else:
        output_f = sys.stdout

    with contextlib.closing(output_f):
        for prediction in predictions:
            output_f.write(json.dumps(prediction.to_dict()) + "\n")


def generate_from_ocr_archive(
    input_: Union[str, TextIO, pathlib.Path],
    prediction_type: PredictionType,
    keep_empty: bool = False,
) -> Iterable[ProductPredictions]:
    for source_image, ocr_json in ocr_iter(input_):
        if source_image is None:
            continue

        barcode: Optional[str] = get_barcode_from_path(source_image)

        if barcode is None:
            click.echo(
                "cannot extract barcode from source " "{}".format(source_image),
                err=True,
            )
            continue

        ocr_result: Optional[OCRResult] = OCRResult.from_json(ocr_json)

        if ocr_result is None:
            continue

        predictions = extract_predictions(ocr_result, prediction_type)

        # Do not produce output if predictions is empty and we don't want to keep it
        if not keep_empty and not predictions:
            continue

        yield ProductPredictions(
            predictions=predictions,
            barcode=barcode,
            type=prediction_type,
            source_image=source_image,
        )


def insights_iter(file_path: pathlib.Path) -> Iterable[ProductPredictions]:
    for insight in jsonl_iter(file_path):
        yield ProductPredictions.from_dict(insight)


def import_insights(
    predictions: Iterable[ProductPredictions],
    server_domain: str,
    batch_size: int = 1024,
) -> int:
    product_store = get_product_store()
    imported: int = 0

    prediction_batch: List[ProductPredictions]
    for prediction_batch in chunked(predictions, batch_size):
        with db.atomic():
            imported += import_insights_(
                prediction_batch,
                server_domain,
                automatic=False,
                product_store=product_store,
            )

    return imported


class InvalidInsight(Exception):
    pass


def is_automatically_processable(
    insight: ProductInsight, max_timedelta: datetime.timedelta
) -> bool:
    if not insight.source_image:
        return False

    image_path = pathlib.Path(insight.source_image)
    image_id = image_path.stem

    if not image_id.isdigit():
        return False

    product = get_product(insight.barcode, fields=["images"])

    if product is None:
        logger.info("Missing product: {}".format(insight.barcode))
        raise InvalidInsight()

    if "images" not in product:
        logger.info("No images for product {}".format(insight.barcode))
        raise InvalidInsight()

    product_images = product["images"]

    if image_id not in product_images:
        logger.info(
            "Missing image for product {}, ID: {}".format(insight.barcode, image_id)
        )
        raise InvalidInsight()

    if is_recent_image(product_images, image_id, max_timedelta):
        return True

    if is_selected_image(product_images, image_id):
        return True

    return False


def is_selected_image(product_images: Dict, image_id: str) -> bool:
    for key_prefix in ("nutrition", "front", "ingredients"):
        for key, image in product_images.items():
            if key.startswith(key_prefix):
                if image["imgid"] == image_id:
                    logger.info(
                        "Image {} is a selected image for "
                        "'{}'".format(image_id, key_prefix)
                    )
                    return True

    return False


def is_recent_image(
    product_images: Dict, image_id: str, max_timedelta: datetime.timedelta
) -> bool:
    upload_datetimes = []
    insight_image_upload_datetime: Optional[datetime.datetime] = None

    for key, image_meta in product_images.items():
        if not key.isdigit():
            continue

        upload_datetime = datetime.datetime.utcfromtimestamp(
            int(image_meta["uploaded_t"])
        )
        if key == image_id:
            insight_image_upload_datetime = upload_datetime
        else:
            upload_datetimes.append(upload_datetime)

    if not upload_datetimes:
        logger.info("No other images")
        return True

    if insight_image_upload_datetime is None:
        raise ValueError("Image with ID {} not found".format(image_id))

    else:
        for upload_datetime in upload_datetimes:
            if upload_datetime - insight_image_upload_datetime > max_timedelta:
                logger.info(
                    "More recent image: {} > {}".format(
                        upload_datetime, insight_image_upload_datetime
                    )
                )
                return False

        sorted_datetimes = [
            str(x)
            for x in sorted(set(x.date() for x in upload_datetimes), reverse=True)
        ]
        logger.info(
            "All images were uploaded the same day or before the target "
            "image:\n{} >= {}".format(
                insight_image_upload_datetime.date(), ", ".join(sorted_datetimes)
            )
        )
        return True

    logger.info(
        "More recent images: {} < {}".format(
            insight_image_upload_datetime.date(),
            max(x.date() for x in upload_datetimes),
        )
    )
    return False


def apply_insights(insight_type: str, max_timedelta: datetime.timedelta):
    logger.info("Timedelta: {}".format(max_timedelta))
    count = 0
    insight: ProductInsight

    annotator = InsightAnnotatorFactory.get(insight_type)
    authorized_labels: Set[str] = AUTHORIZED_LABELS_STORE.get()

    for insight in (
        ProductInsight.select()
        .where(
            ProductInsight.type == insight_type,
            ProductInsight.annotation.is_null(),
            ProductInsight.latent == False,  # noqa: E712
        )
        .order_by(fn.Random())
    ):
        if (
            insight.process_after is not None
            and insight.process_after >= datetime.datetime.utcnow()
        ):
            continue

        if (
            insight_type == InsightType.label.name
            and insight.value_tag not in authorized_labels
        ):
            continue

        try:
            is_processable = is_automatically_processable(insight, max_timedelta)
        except InvalidInsight:
            logger.info("Deleting insight {}".format(insight.id))
            insight.delete_instance()
            continue

        if is_processable:
            logger.info(
                "Annotating insight {} (barcode: {})".format(
                    insight.value_tag or insight.value, insight.barcode
                )
            )
            annotator.annotate(insight, 1, update=True, automatic=True)
            count += 1

    logger.info("Annotated insights: {}".format(count))
