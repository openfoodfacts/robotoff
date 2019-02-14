import contextlib
import json
import sys
from typing import Optional

from robotoff.insights.ocr import (ocr_iter, OCRResult,
                                   get_ocr_result, extract_insights,
                                   get_barcode_from_path)


def run(input_: str, insight_type: str, output: Optional[str]):
    if output is not None:
        output = open(output, 'w')
    else:
        output = sys.stdout

    with contextlib.closing(output):
        for source, ocr_json in ocr_iter(input_):
            ocr_result: OCRResult = get_ocr_result(ocr_json)

            if ocr_result is None:
                continue

            insights = extract_insights(ocr_result, insight_type)

            if insights:
                item = {
                    'insights': insights,
                    'barcode': get_barcode_from_path(source),
                    'type': insight_type,
                }

                if source:
                    item['source'] = source

                output.write(json.dumps(item) + '\n')
