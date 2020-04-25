import contextlib
import json
import pathlib
import sys
from typing import Optional

import click
from more_itertools import chunked

from robotoff.insights.importer import InsightImporterFactory
from robotoff.insights.ocr import (
    ocr_iter,
    OCRResult,
    extract_insights,
    get_barcode_from_path,
)
from robotoff.models import db
from robotoff.products import CACHED_PRODUCT_STORE
from robotoff.utils import gzip_jsonl_iter, jsonl_iter


def run_from_ocr_archive(
    input_: str, insight_type: str, output: Optional[str], keep_empty: bool = False
):
    if output is not None:
        output_f = open(output, "w")
    else:
        output_f = sys.stdout

    with contextlib.closing(output_f):
        for source, ocr_json in ocr_iter(input_):
            if source is None:
                continue

            barcode: Optional[str] = get_barcode_from_path(source)

            if barcode is None:
                click.echo(
                    "cannot extract barcode from source " "{}".format(source), err=True
                )
                continue

            ocr_result: Optional[OCRResult] = OCRResult.from_json(ocr_json)

            if ocr_result is None:
                continue

            insights = extract_insights(ocr_result, insight_type)

            # Do not produce output if insights is empty and we don't want to keep it
            if not keep_empty and not insights:
                continue

            item = {
                "insights": insights,
                "barcode": barcode,
                "type": insight_type,
            }

            if source:
                item["source"] = source

            output_f.write(json.dumps(item) + "\n")


def import_insights(
    file_path: pathlib.Path,
    insight_type: str,
    server_domain: str,
    batch_size: int = 1024,
) -> int:
    product_store = CACHED_PRODUCT_STORE.get()
    importer = InsightImporterFactory.create(insight_type, product_store)

    if file_path.suffix == ".gz":
        insights = gzip_jsonl_iter(file_path)
    else:
        insights = jsonl_iter(file_path)

    imported: int = 0

    for insight_batch in chunked(insights, batch_size):
        with db.atomic():
            imported += importer.import_insights(
                insight_batch, server_domain=server_domain, automatic=False
            )

    return imported
