import contextlib
import json
import sys
from typing import Optional

import click

from robotoff.insights.ocr import (ocr_iter, OCRResult,
                                   get_ocr_result, extract_insights,
                                   get_barcode_from_path)


def run(input_: str, insight_type: str, output: Optional[str]):
    if output is not None:
        output_f = open(output, 'w')
    else:
        output_f = sys.stdout

    with contextlib.closing(output_f):
        for source, ocr_json in ocr_iter(input_):
            if source is None:
                continue

            barcode: Optional[str] = get_barcode_from_path(source)

            if barcode is None:
                click.echo("cannot extract barcode from source "
                           "{}".format(source), err=True)
                continue

            ocr_result: Optional[OCRResult] = get_ocr_result(ocr_json)

            if ocr_result is None:
                continue

            insights = extract_insights(ocr_result, insight_type)

            if insights:
                item = {
                    'insights': insights,
                    'barcode': barcode,
                    'type': insight_type,
                }

                if source:
                    item['source'] = source

                output_f.write(json.dumps(item) + '\n')
