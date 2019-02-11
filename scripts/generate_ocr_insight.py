# -*- coding: utf-8 -*-
import contextlib
import gzip
import re
import argparse
import json
import sys

import pathlib as pathlib
from typing import List, Dict, Any, Iterable, Optional

import requests


def process_fr_packaging_match(match) -> str:
    country_code, *approval_numbers, ec = match.group(1, 2, 3, 4, 5)
    return "{} {}.{}.{} {}".format(country_code, *approval_numbers, ec)


def process_fr_emb_match(match) -> str:
    emb_str, city_code, company_code = match.group(1, 2, 3)
    city_code = city_code.replace(' ', '')
    company_code = company_code or ''
    return "{} {}{}".format(emb_str, city_code, company_code)


NUTRISCORE_REGEX = re.compile(r"nutri[-\s]?score", re.IGNORECASE)
WEIGHT_MENTIONS = (
    "poids net:",
    "poids net égoutté:",
    "net weight:",
    "peso neto:",
    "peso liquido:",
    "netto gewicht:",
)

WEIGHT_MENTIONS_RE = re.compile('|'.join((re.escape(x)
                                          for x in WEIGHT_MENTIONS)),
                                re.IGNORECASE)

WEIGHT_VALUES_REGEX = re.compile(
    r"([0-9]+[,.]?[0-9]*)\s*(fl oz|dl|cl|mg|mL|lbs|oz|g|kg|L)(?![^\s])")

URL_REGEX = re.compile(r'^(http://www\.|https://www\.|http://|https://)?[a-z0-9]+([\-.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(/.*)?$')
EMAIL_REGEX = re.compile(r'[\w.-]+@[\w.-]+')
PHONE_REGEX = re.compile(r'\d{3}[-.\s]??\d{3}[-.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-.\s]??\d{4}|\d{3}[-.\s]??\d{4}')

PACKAGER_CODE = {
    "fr_emb": (re.compile(r"(EMB) ?(\d ?\d ?\d ?\d ?\d)([a-zA-Z]{1,2})?"),
               process_fr_emb_match),
    "eu_fr": (re.compile("(FR) (\d{1,3})[\-\s.](\d{1,3})[\-\s.](\d{1,3}) (CE|EC)"),
              process_fr_packaging_match),
}

RECYCLING_REGEX = {
    'recycling': [
        re.compile(r"recycle", re.IGNORECASE),
    ],
    'throw_away': [
        re.compile(r"(?:throw away)|(?:jeter)", re.IGNORECASE)
    ]
}

LABELS_REGEX = {
    'en:organic': [
        re.compile(r"ingr[ée]dients?\sbiologiques?", re.IGNORECASE),
        re.compile(r"agriculture ue/non ue biologique", re.IGNORECASE),
    ],
}

BEST_BEFORE_DATE_REGEX = {
    'en': re.compile(r'\d\d\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s\d{4})?', re.IGNORECASE),
    'fr': re.compile(r'\d\d\s(?:Jan|Fev|Mar|Avr|Mai|Juin|Juil|Aou|Sep|Oct|Nov|Dec)(?:\s\d{4})?', re.IGNORECASE),
    'full_digits': re.compile(r'\d{2}[./]\d{2}[./](?:\d{2}){1,2}'),
}


def get_barcode_from_path(path: str):
    path = pathlib.Path(path)

    barcode = ''

    for parent in path.parents:
        if parent.name.isdigit():
            barcode = parent.name + barcode
        else:
            break

    barcode = barcode or None
    return barcode


def split_barcode(barcode: str):
    return barcode[0:3], barcode[3:6], barcode[6:9], barcode[9:13]


def fetch_images_for_ean(ean: str):
    url = "https://world.openfoodfacts.org/api/v0/product/" \
          "{}.json?fields=images".format(ean)
    images = requests.get(url).json()
    return images


def get_json_for_image(barcode: str, image_name: str) -> \
        Optional[Dict[str, Any]]:
    splitted_barcode = split_barcode(barcode)
    url = "https://static.openfoodfacts.org/images/products/{}/{}/{}/{}/" \
          "{}.json".format(splitted_barcode[0], splitted_barcode[1],
                           splitted_barcode[2], splitted_barcode[3],
                           image_name)
    r = requests.get(url)

    if r.status_code == 404:
        return

    return r.json()


def ocr_text_iter(data: Dict[str, Any]) -> Iterable[str]:
    responses = data.get('responses', [])

    if not responses:
        return

    response = responses[0]
    full_text_annotation = response.get('fullTextAnnotation')

    if full_text_annotation:
        text = full_text_annotation.get('text')

        if text is not None:
            yield text

    else:
        text_annotations = response.get('textAnnotations', [])

        for text_annotation in text_annotations:
            text = text_annotation.get('description')

            if text is not None:
                yield text


def find_emails(text: str) -> List[Dict]:
    results = []

    for match in EMAIL_REGEX.finditer(text):
        results.append({
            "text": match.group(),
        })

    return results


def find_urls(text: str) -> List[Dict]:
    results = []
    for match in URL_REGEX.finditer(text):
        results.append({
            "text": match.group(),
        })

    return results


def find_packager_codes(text: str) -> List[Dict]:
    results = []

    for regex_code, (regex, processing_func) in PACKAGER_CODE.items():
        for match in regex.finditer(text):
            value = processing_func(match)
            results.append({
                "raw": match.group(0),
                "text": value,
                "type": regex_code,
            })

    return results


def find_weight_values(text: str) -> List[Dict]:
    weight_values = []

    for match in WEIGHT_VALUES_REGEX.finditer(text):
        result = {
            'text': match.group(),
            'value': match.group(1),
            'unit': match.group(2),
        }
        weight_values.append(result)

    return weight_values


def find_weight_mentions(text: str) -> List[Dict]:
    weight_mentions = []

    for match in WEIGHT_MENTIONS_RE.finditer(text):
        result = {
            'text': match.group(),
        }
        weight_mentions.append(result)

    return weight_mentions


TEMPERATURE_REGEX_STR = r"[+-]?\s*\d+\s*°?C"
TEMPERATURE_REGEX = re.compile(r"(?P<value>[+-]?\s*\d+)\s*°?(?P<unit>C)",
                               re.IGNORECASE)

STORAGE_INSTRUCTIONS_REGEX = {
    'max': re.compile(r"[aà] conserver [àa] ({0}) maximum".format(
        TEMPERATURE_REGEX_STR), re.IGNORECASE),
    'between': re.compile(r"[aà] conserver entre ({0}) et ({0})".format(
        TEMPERATURE_REGEX_STR), re.IGNORECASE),
}


def extract_temperature_information(temperature: str) -> Dict:
    match = TEMPERATURE_REGEX.match(temperature)

    if match:
        result = {}
        value = match.group('value')
        unit = match.group('unit')

        if value:
            result['value'] = value

        if unit:
            result['unit'] = unit

        return result


def find_storage_instructions(text: str) -> List[Dict]:
    text = text.lower()

    results = []

    for instruction_type, regex in STORAGE_INSTRUCTIONS_REGEX.items():
        for match in regex.finditer(text):
            if match:
                result = {
                    'text': match.group(),
                    'type': instruction_type,
                }

                if instruction_type == 'max':
                    result['max'] = extract_temperature_information(
                        match.group(1))

                elif instruction_type == 'between':
                    result['between'] = {
                        'min': extract_temperature_information(match.group(1)),
                        'max': extract_temperature_information(match.group(2)),
                    }

                results.append(result)

    return results


def find_nutriscore(text: str) -> List[Dict]:
    results = []
    for match in NUTRISCORE_REGEX.finditer(text):
        results.append({
            "text": match.group(),
        })

    return results


def find_phone_numbers(text) -> List[Dict]:
    results = []

    for match in PHONE_REGEX.finditer(text):
        results.append({
            "text": match.group(),
        })

    return results


def find_recycling_instructions(text) -> List[Dict]:
    results = []

    for instruction_type, regex_list in RECYCLING_REGEX.items():
        for regex in regex_list:
            for match in regex.finditer(text):
                results.append({
                    'type': instruction_type,
                    'text': match.group(),
                })

    return results


def find_labels(text: str) -> List[Dict]:
    text = text.lower()

    results = []

    for label_type, regex_list in LABELS_REGEX.items():
        for regex in regex_list:
            for match in regex.finditer(text):
                results.append({
                    'type': label_type,
                    'text': match.group(),
                })

    return results


def find_best_before_date(text: str) -> List[Dict]:
    # Parse best_before_date
    #        "À consommer de préférence avant",
    results = []

    for type_, regex in BEST_BEFORE_DATE_REGEX.items():
        for match in regex.finditer(text):
            results.append({
                "text": match.group(),
                "type": type_,
            })

    return results


def extract_insights(data: Dict[str, Any],
                     insight_type: str) -> List[Dict]:
    extracted = []

    for text in ocr_text_iter(data):
        contiguous_text = text.replace('\n', ' ')

        if insight_type == 'weight_value':
            extracted += find_weight_values(text)

        elif insight_type == 'weight_mention':
            extracted += find_weight_mentions(text)

        elif insight_type == 'packager_code':
            extracted += find_packager_codes(contiguous_text)

        elif insight_type == 'nutriscore':
            extracted += find_nutriscore(text)

        elif insight_type == 'recycling_instruction':
            extracted += find_recycling_instructions(contiguous_text)

        elif insight_type == 'email':
            extracted += find_emails(text)

        elif insight_type == 'url':
            extracted += find_urls(text)

        elif insight_type == 'label':
            extracted += find_labels(contiguous_text)

        elif insight_type == 'storage_instruction':
            extracted += find_storage_instructions(contiguous_text)

        elif insight_type == 'best_before_date':
            extracted += find_best_before_date(text)
        else:
            raise ValueError("unknown insight type: {}".format(insight_type))

    return extracted


def is_barcode(text: str):
    return len(text) == 13 and text.isdigit()


def get_source(image_name: str, json_path: str = None, barcode: str = None):
    if not barcode:
        barcode = get_barcode_from_path(str(json_path))

    return "/{}/{}.jpg" \
           "".format('/'.join(split_barcode(barcode)),
                     image_name)


def ocr_iter(input_str: str):
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

                            if not pathlib.Path(source).stem.isdigit():
                                continue

                            yield source, json_data['content']


def get_ocr_from_barcode(barcode: str):
    image_data = fetch_images_for_ean(barcode)['product']['images']

    for image_name in image_data.keys():
        if image_name.isdigit():
            print("Getting OCR for image {}".format(image_name))
            data = get_json_for_image(barcode, image_name)
            return data


def run(args: argparse.Namespace):
    input_ = args.input

    if args.output is not None:
        output = open(args.output, 'w')
    else:
        output = sys.stdout

    with contextlib.closing(output):
        for source, ocr_json in ocr_iter(input_):
            insights = extract_insights(ocr_json, args.insight_type)

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
