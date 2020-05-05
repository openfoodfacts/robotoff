import gzip
import json

import pathlib as pathlib
from typing import Callable, List, Dict, Iterable, Optional, Tuple, Union, TextIO

from robotoff.insights._enum import InsightType
from robotoff.insights.ocr.brand import find_brands
from robotoff.insights.ocr.dataclass import OCRResult
from robotoff.insights.ocr.expiration_date import find_expiration_date
from robotoff.insights.ocr.image_flag import flag_image
from robotoff.insights.ocr.image_lang import get_image_lang
from robotoff.insights.ocr.image_orientation import find_image_orientation
from robotoff.insights.ocr.label import find_labels
from robotoff.insights.ocr.location import find_locations
from robotoff.insights.ocr.nutrient import find_nutrient_mentions, find_nutrient_values
from robotoff.insights.ocr.packager_code import find_packager_codes
from robotoff.insights.ocr.packaging import find_packaging
from robotoff.insights.ocr.product_weight import find_product_weight
from robotoff.insights.ocr.store import find_stores
from robotoff.insights.ocr.trace import find_traces
from robotoff.off import generate_json_ocr_url, split_barcode, http_session
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


def get_barcode_from_path(path: str) -> Optional[str]:
    barcode = ""

    for parent in pathlib.Path(path).parents:
        if parent.name.isdigit():
            barcode = parent.name + barcode
        else:
            break

    return barcode or None


def fetch_images_for_ean(ean: str):
    url = (
        "https://world.openfoodfacts.org/api/v0/product/"
        "{}.json?fields=images".format(ean)
    )
    images = http_session.get(url).json()
    return images


def get_json_for_image(barcode: str, image_name: str) -> Optional[JSONType]:
    url = generate_json_ocr_url(barcode, image_name)
    r = http_session.get(url)

    if r.status_code == 404:
        return None

    return r.json()


def extract_insights(content: Union[OCRResult, str], insight_type: str) -> List[Dict]:
    if insight_type == InsightType.packager_code.name:
        return find_packager_codes(content)

    elif insight_type == InsightType.label.name:
        return find_labels(content)

    elif insight_type == InsightType.expiration_date.name:
        return find_expiration_date(content)

    elif insight_type == InsightType.image_flag.name:
        return flag_image(content)

    elif insight_type == InsightType.image_orientation.name:
        return find_image_orientation(content)

    elif insight_type == InsightType.product_weight.name:
        return find_product_weight(content)

    elif insight_type == InsightType.trace.name:
        return find_traces(content)

    elif insight_type == InsightType.nutrient.name:
        return find_nutrient_values(content)

    elif insight_type == InsightType.nutrient_mention.name:
        return find_nutrient_mentions(content)

    elif insight_type == InsightType.brand.name:
        return find_brands(content)

    elif insight_type == InsightType.store.name:
        return find_stores(content)

    elif insight_type == InsightType.packaging.name:
        return find_packaging(content)

    elif insight_type == InsightType.location.name:
        return find_locations(content)

    elif insight_type == InsightType.image_lang.name:
        return get_image_lang(content)

    else:
        raise ValueError("unknown insight type: {}".format(insight_type))


def is_barcode(text: str):
    return text.isdigit()


def get_source(
    image_name: str, json_path: str = None, barcode: Optional[str] = None
) -> str:
    if not barcode:
        barcode = get_barcode_from_path(str(json_path))

        if not barcode:
            raise ValueError("invalid JSON path: {}".format(json_path))

    return "/{}/{}.jpg" "".format("/".join(split_barcode(barcode)), image_name)


def ocr_iter_jsonl(stream: TextIO) -> Iterable[Tuple[Optional[str], Dict]]:
    for line in stream:
        json_data = json.loads(line)

        if "content" in json_data:
            source = json_data["source"].replace("//", "/").replace(".json", ".jpg")
            yield source, json_data["content"]


def ocr_iter(source: Union[str, TextIO]) -> Iterable[Tuple[Optional[str], Dict]]:
    if not isinstance(source, str):
        yield from ocr_iter_jsonl(source)

    elif is_barcode(source):
        barcode: str = source
        image_data = fetch_images_for_ean(source)["product"]["images"]

        for image_name in image_data.keys():
            if image_name.isdigit():
                print("Getting OCR for image {}".format(image_name))
                data = get_json_for_image(barcode, image_name)
                source = get_source(image_name, barcode=barcode)
                if data:
                    yield source, data

    else:
        input_path = pathlib.Path(source)

        if not input_path.exists():
            print("Unrecognized input: {}".format(input_path))
            return

        if input_path.is_dir():
            for json_path in input_path.glob("**/*.json"):
                with open(str(json_path), "r") as f:
                    source = get_source(json_path.stem, json_path=str(json_path))
                    yield source, json.load(f)
        else:
            if ".json" in input_path.suffixes:
                with open(str(input_path), "r") as f:
                    yield None, json.load(f)

            elif ".jsonl" in input_path.suffixes:
                open_func: Callable
                if input_path.suffix == ".gz":
                    open_func = gzip.open
                else:
                    open_func = open

                with open_func(input_path, mode="rt") as f:
                    yield from ocr_iter_jsonl(f)
