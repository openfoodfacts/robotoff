import contextlib
import json
import pathlib
import sys
from typing import Iterable, List, Optional, TextIO, Union

import _io
import click
import dacite
from more_itertools import chunked

from robotoff.insights.importer import import_insights as import_insights_
from robotoff.models import db
from robotoff.off import get_barcode_from_path
from robotoff.prediction.ocr import OCRResult, extract_predictions, ocr_iter
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.products import get_product_store
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
