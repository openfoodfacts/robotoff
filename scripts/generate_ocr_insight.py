# -*- coding: utf-8 -*-
import contextlib
import argparse
import json
import sys

from robotoff.insights.ocr import ocr_iter, get_ocr_result, OCRResult, extract_insights, get_barcode_from_path


def run(args: argparse.Namespace):
    input_ = args.input

    if args.output is not None:
        output = open(args.output, 'w')
    else:
        output = sys.stdout

    with contextlib.closing(output):
        for source, ocr_json in ocr_iter(input_):
            ocr_result: OCRResult = get_ocr_result(ocr_json)

            if ocr_result is None:
                continue

            insights = extract_insights(ocr_result, args.insight_type)

            if insights:
                item = {
                    'insights': insights,
                    'barcode': get_barcode_from_path(source),
                    'type': args.insight_type,
                }

                if source:
                    item['source'] = source

                output.write(json.dumps(item) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('--insight-type', required=True)
    parser.add_argument('--output', '-o')
    arguments = parser.parse_args()
    run(arguments)
