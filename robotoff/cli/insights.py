import contextlib
import gzip
import sys
from pathlib import Path
from typing import Iterable, Optional

import _io
import click
import dacite
import orjson
import tqdm

from robotoff.off import get_barcode_from_path
from robotoff.prediction.ocr import OCRResult, extract_predictions
from robotoff.prediction.ocr.core import ocr_content_iter
from robotoff.prediction.types import Prediction
from robotoff.types import PredictionType
from robotoff.utils import get_logger, gzip_jsonl_iter, jsonl_iter

logger = get_logger(__name__)


def run_from_ocr_archive(
    input_path: Path,
    prediction_type: PredictionType,
    output: Optional[Path] = None,
):
    predictions = tqdm.tqdm(
        generate_from_ocr_archive(input_path, prediction_type), desc="OCR"
    )
    output_f: _io._TextIOBase
    need_decoding = False

    if output is not None:
        if output.suffix == ".gz":
            output_f = gzip.open(output, "wb")
        else:
            output_f = output.open("wb")
    else:
        output_f = sys.stdout
        need_decoding = True

    with contextlib.closing(output_f):
        for prediction in predictions:
            raw_data = orjson.dumps(prediction.to_dict()) + b"\n"
            data = raw_data.decode("utf-8") if need_decoding else raw_data
            output_f.write(data)


def generate_from_ocr_archive(
    input_path: Path,
    prediction_type: PredictionType,
) -> Iterable[Prediction]:
    json_iter = (
        gzip_jsonl_iter(input_path)
        if input_path.suffix == ".gz"
        else jsonl_iter(input_path)
    )
    for source_image, ocr_json in ocr_content_iter(json_iter):
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


def insights_iter(file_path: Path) -> Iterable[Prediction]:
    for prediction in jsonl_iter(file_path):
        yield dacite.from_dict(
            data_class=Prediction,
            data=prediction,
            config=dacite.Config(cast=[PredictionType]),
        )
