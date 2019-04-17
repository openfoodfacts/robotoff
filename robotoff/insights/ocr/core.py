# -*- coding: utf-8 -*-
import gzip
import json

import pathlib as pathlib
from typing import List, Dict, Iterable, Optional, Tuple
from urllib.parse import urlparse

import requests

from robotoff.insights._enum import InsightType
from robotoff.insights.ocr.brand import find_brands
from robotoff.insights.ocr.dataclass import OCRResult
from robotoff.insights.ocr.expiration_date import find_expiration_date
from robotoff.insights.ocr.image_flag import flag_image
from robotoff.insights.ocr.image_orientation import find_image_orientation
from robotoff.insights.ocr.label import find_labels
from robotoff.insights.ocr.nutrient import find_nutrient_values
from robotoff.insights.ocr.packager_code import find_packager_codes
from robotoff.insights.ocr.product_weight import find_product_weight
from robotoff.insights.ocr.trace import find_traces
from robotoff.off import generate_json_ocr_url, split_barcode
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def get_barcode_from_path(path: str) -> Optional[str]:
    barcode = ''

    for parent in pathlib.Path(path).parents:
        if parent.name.isdigit():
            barcode = parent.name + barcode
        else:
            break

    return barcode or None


def fetch_images_for_ean(ean: str):
    url = "https://world.openfoodfacts.org/api/v0/product/" \
          "{}.json?fields=images".format(ean)
    images = requests.get(url).json()
    return images


def get_json_for_image(barcode: str, image_name: str) -> \
        Optional[JSONType]:
    url = generate_json_ocr_url(barcode, image_name)
    r = requests.get(url)

    if r.status_code == 404:
        return None

    return r.json()


def extract_insights(ocr_result: OCRResult,
                     insight_type: str) -> List[Dict]:
    if insight_type == 'packager_code':
        return find_packager_codes(ocr_result)

    elif insight_type == 'label':
        return find_labels(ocr_result)

    elif insight_type == 'expiration_date':
        return find_expiration_date(ocr_result)

    elif insight_type == 'image_flag':
        return flag_image(ocr_result)

    elif insight_type == 'image_orientation':
        return find_image_orientation(ocr_result)

    elif insight_type == 'product_weight':
        return find_product_weight(ocr_result)

    elif insight_type == 'trace':
        return find_traces(ocr_result)

    elif insight_type == 'nutrient':
        return find_nutrient_values(ocr_result)

    elif insight_type == 'brand':
        return find_brands(ocr_result)

    else:
        raise ValueError("unknown insight type: {}".format(insight_type))


def is_barcode(text: str):
    return text.isdigit()


def get_source(image_name: str, json_path: str = None, barcode: str = None):
    if not barcode:
        barcode = get_barcode_from_path(str(json_path))

    return "/{}/{}.jpg" \
           "".format('/'.join(split_barcode(barcode)),
                     image_name)


def ocr_iter(input_str: str) -> Iterable[Tuple[Optional[str], Dict]]:
    if is_barcode(input_str):
        image_data = fetch_images_for_ean(input_str)['product']['images']

        for image_name in image_data.keys():
            if image_name.isdigit():
                print("Getting OCR for image {}".format(image_name))
                data = get_json_for_image(input_str, image_name)
                source = get_source(image_name, barcode=input_str)
                if data:
                    yield source, data

    else:
        input_path = pathlib.Path(input_str)

        if not input_path.exists():
            print("Unrecognized input: {}".format(input_path))
            return

        if input_path.is_dir():
            for json_path in input_path.glob("**/*.json"):
                with open(str(json_path), 'r') as f:
                    source = get_source(json_path.stem,
                                        json_path=str(json_path))
                    yield source, json.load(f)
        else:
            if '.json' in input_path.suffixes:
                with open(str(input_path), 'r') as f:
                    yield None, json.load(f)

            elif '.jsonl' in input_path.suffixes:
                if input_path.suffix == '.gz':
                    open_func = gzip.open
                else:
                    open_func = open

                with open_func(input_path, mode='rt') as f:
                    for line in f:
                        json_data = json.loads(line)

                        if 'content' in json_data:
                            source = json_data['source'].replace('//', '/')
                            yield source, json_data['content']


def get_insights_from_image(barcode: str, image_url: str, ocr_url: str) \
        -> Optional[Dict]:
    r = requests.get(ocr_url)

    if r.status_code == 404:
        return None

    r.raise_for_status()

    ocr_data: Dict = requests.get(ocr_url).json()
    ocr_result = OCRResult.from_json(ocr_data)

    if ocr_result is None:
        return None

    image_url_path = urlparse(image_url).path

    if image_url_path.startswith('/images/products'):
        image_url_path = image_url_path[len("/images/products"):]

    results = {}

    for insight_type in (InsightType.label.name,
                         InsightType.packager_code.name,
                         InsightType.product_weight.name,
                         InsightType.image_flag.name,
                         InsightType.expiration_date.name,
                         InsightType.brand.name):
        insights = extract_insights(ocr_result, insight_type)

        if insights:
            results[insight_type] = {
                'insights': insights,
                'barcode': barcode,
                'type': insight_type,
                'source': image_url_path,
            }

    return results
