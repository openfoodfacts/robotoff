import contextlib
import gzip
import sys
from pathlib import Path
from typing import Iterable, Optional

import _io
import dacite
import orjson
import tqdm

from robotoff.insights.extraction import DEFAULT_OCR_PREDICTION_TYPES
from robotoff.off import get_barcode_from_path
from robotoff.prediction.ocr import OCRResult, extract_predictions
from robotoff.prediction.ocr.core import ocr_content_iter
from robotoff.types import Prediction, PredictionType, ProductIdentifier, ServerType
from robotoff.utils import get_logger, jsonl_iter

logger = get_logger(__name__)


def run_from_ocr_archive(
    input_path: Path,
    prediction_types: Optional[list[PredictionType]],
    server_type: ServerType,
    output: Optional[Path] = None,
):
    """Generate predictions from an OCR archive file and save these
    predictions on-disk or send them to stdout.

    :param input_path: path of the archive file (gzipped JSONL)
    :param prediction_types: list of prediction types to extract, if None
        default OCR predictions types will be extracted (see
        robotoff.insights.extraction.DEFAULT_OCR_PREDICTION_TYPES).
    :param server_type: server type associated with the OCR archive.
    :param output: the file path where to save the predictions, or None if
        the JSON should be sent to stdout, defaults to None.
    """
    predictions = tqdm.tqdm(
        generate_from_ocr_archive(input_path, prediction_types, server_type),
        desc="prediction",
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
    prediction_types: Optional[list[PredictionType]],
    server_type: ServerType,
) -> Iterable[Prediction]:
    """Generate predictions from an OCR archive file.

    :param input_path: path of the archive file (gzipped JSONL)
    :param prediction_types: list of prediction types to extract, if None
        default OCR predictions types will be extracted (see
        robotoff.insights.extraction.DEFAULT_OCR_PREDICTION_TYPES).
    :param server_type: server type associated with the OCR archive.
    :yield: the extracted `Prediction`s
    """
    if prediction_types is None:
        prediction_types = DEFAULT_OCR_PREDICTION_TYPES

    for source_image, ocr_json in ocr_content_iter(
        tqdm.tqdm(jsonl_iter(input_path), desc="OCR")
    ):
        if source_image is None:
            continue

        barcode: Optional[str] = get_barcode_from_path(source_image)

        if barcode is None:
            logger.warning("cannot extract barcode from source", source_image)
            continue

        ocr_result: Optional[OCRResult] = OCRResult.from_json(ocr_json)

        if ocr_result is None:
            continue

        for prediction_type in prediction_types:
            yield from extract_predictions(
                ocr_result,
                prediction_type,
                product_id=ProductIdentifier(barcode=barcode, server_type=server_type),
                source_image=source_image,
            )


def insights_iter(file_path: Path) -> Iterable[Prediction]:
    for prediction in jsonl_iter(file_path):
        yield dacite.from_dict(
            data_class=Prediction,
            data=prediction,
            config=dacite.Config(cast=[PredictionType]),
        )
