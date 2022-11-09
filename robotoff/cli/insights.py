import contextlib
import datetime
import functools
import json
import pathlib
import sys
from typing import Iterable, List, Optional, Set, TextIO, Union

import _io
import click
import dacite
from more_itertools import chunked
from peewee import fn

from robotoff.insights import InsightType
from robotoff.insights.annotate import InsightAnnotatorFactory
from robotoff.insights.importer import AUTHORIZED_LABELS_STORE
from robotoff.insights.importer import import_insights as import_insights_
from robotoff.insights.importer import is_recent_image, is_selected_image
from robotoff.models import ProductInsight, db
from robotoff.off import get_barcode_from_path
from robotoff.prediction.ocr import OCRResult, extract_predictions, ocr_iter
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.products import get_product, get_product_store
from robotoff.utils import get_logger, jsonl_iter

logger = get_logger(__name__)


def run_from_ocr_archive(
    input_: Union[str, TextIO],
    prediction_type: PredictionType,
    output: Optional[pathlib.Path] = None,
):
    predictions = generate_from_ocr_archive(input_, prediction_type)
    output_f: _io._TextIOBase

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
) -> Iterable[Prediction]:
    for source_image, ocr_json in ocr_iter(input_):
        if source_image is None:
            continue

        barcode: Optional[str] = get_barcode_from_path(source_image)

        if barcode is None:
            click.echo(
                f"cannot extract barcode from source {source_image}",
                err=True,
            )
            continue

        ocr_result: Optional[OCRResult] = OCRResult.from_json(ocr_json)

        if ocr_result is None:
            continue

        yield from extract_predictions(
            ocr_result, prediction_type, barcode=barcode, source_image=source_image
        )


def insights_iter(file_path: pathlib.Path) -> Iterable[Prediction]:
    for prediction in jsonl_iter(file_path):
        yield dacite.from_dict(
            data_class=Prediction,
            data=prediction,
            config=dacite.Config(cast=[PredictionType]),
        )


def import_insights(
    predictions: Iterable[Prediction],
    server_domain: str,
    batch_size: int = 1024,
) -> int:
    product_store = get_product_store()
    imported: int = 0

    prediction_batch: List[Prediction]
    for prediction_batch in chunked(predictions, batch_size):
        with db.atomic():
            imported += import_insights_(
                prediction_batch,
                server_domain,
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

    product = get_product(insight.barcode, projection=["images"])

    if product is None:
        logger.info(f"Missing product: {insight.barcode}")
        raise InvalidInsight()

    if "images" not in product:
        logger.info(f"No images for product {insight.barcode}")
        raise InvalidInsight()

    product_images = product["images"]

    if image_id not in product_images:
        logger.info(f"Missing image for product {insight.barcode}, ID: {image_id}")
        raise InvalidInsight()

    return is_recent_image(
        product_images, image_id, max_timedelta
    ) or is_selected_image(product_images, image_id)


def generate_apply_insights_query(
    insight_type: str,
    predictor: str,
    value_tag: Optional[str] = None,
    max_scan_count: Optional[int] = None,
):
    where_clauses = [
        ProductInsight.type == insight_type,
        ProductInsight.annotation.is_null(),
        ProductInsight.predictor == predictor,
    ]
    if value_tag is not None:
        where_clauses.append(ProductInsight.value_tag == value_tag)

    if max_scan_count is not None:
        where_clauses.append(ProductInsight.unique_scans_n <= max_scan_count)

    return ProductInsight.select().where(*where_clauses)


def apply_insights(
    insight_type: str,
    predictor: str,
    max_timedelta: datetime.timedelta,
    value_tag: Optional[str] = None,
    max_scan_count: Optional[int] = None,
    dry_run: bool = False,
):
    """Apply automatically insights based on the following criteria:
    - their insight type
    - their predictor value
    - the maximum number of days between the upload of the insight image and
    the upload of the most recent image of the product

    If the insight is invalid (the image the insight is based on has been
    deleted or the product does not exist), the insight will be deleted.

    :param insight_type: filter based on insight type
    :param predictor: filter based on predictor value
    :param max_timedelta: maximum image timestamp timedelta
    :param value_tag: filter based on `value_tag` (optional)
    :param max_scan_count: filter based on their scan count
    (<= max_scan_count, optional)
    :param dry_run: if True, doesn't perform any database edit or insight
    deletion
    """
    logger.info(f"Timedelta: {max_timedelta}")
    count = 0
    insight: ProductInsight

    annotator = InsightAnnotatorFactory.get(insight_type)
    authorized_labels: Set[str] = AUTHORIZED_LABELS_STORE.get()
    query_func = functools.partial(
        generate_apply_insights_query,
        insight_type=insight_type,
        predictor=predictor,
        value_tag=value_tag,
        max_scan_count=max_scan_count,
    )
    logger.info(f"Number of insights to check: {query_func().count()}")

    for insight in query_func().order_by(fn.Random()):
        if insight.process_after is not None:
            continue

        if (
            insight_type == InsightType.label.name
            and insight.value_tag not in authorized_labels
        ):
            continue

        try:
            is_processable = is_automatically_processable(insight, max_timedelta)
        except InvalidInsight:
            logger.info(f"Deleting insight {insight.id}")

            if not dry_run:
                insight.delete_instance()
            continue

        if is_processable:
            logger.info(
                f"Annotating insight {insight.value_tag or insight.value} (barcode: {insight.barcode})"
            )
            if not dry_run:
                annotator.annotate(insight, 1, update=True, automatic=True)
            count += 1

    logger.info(f"Annotated insights: {count}")
