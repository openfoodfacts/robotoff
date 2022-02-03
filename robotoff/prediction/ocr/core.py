import pathlib
from typing import Dict, Iterable, List, Optional, TextIO, Tuple, Union

import orjson

from robotoff.off import generate_json_ocr_url, split_barcode
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.settings import BaseURLProvider
from robotoff.utils import get_logger, http_session, jsonl_iter, jsonl_iter_fp
from robotoff.utils.types import JSONType

from .brand import find_brands
from .dataclass import OCRResult
from .expiration_date import find_expiration_date
from .image_flag import flag_image
from .image_lang import get_image_lang
from .image_orientation import find_image_orientation
from .label import find_labels
from .location import find_locations
from .nutrient import find_nutrient_mentions, find_nutrient_values
from .packager_code import find_packager_codes
from .packaging import find_packaging
from .product_weight import find_product_weight
from .store import find_stores
from .trace import find_traces

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
    url = BaseURLProvider().get() + "/api/v0/product/{}.json?fields=images".format(ean)
    images = http_session.get(url).json()
    return images


def get_json_for_image(barcode: str, image_id: str) -> Optional[JSONType]:
    url = generate_json_ocr_url(barcode, image_id)
    r = http_session.get(url)

    if r.status_code == 404:
        return None

    return r.json()


def extract_predictions(
    content: Union[OCRResult, str], prediction_type: PredictionType
) -> List[Prediction]:
    """Proxy to each predictor, depending on prediction type."""
    if prediction_type == PredictionType.packager_code:
        return find_packager_codes(content)

    elif prediction_type == PredictionType.label:
        return find_labels(content)

    elif prediction_type == PredictionType.expiration_date:
        return find_expiration_date(content)

    elif prediction_type == PredictionType.image_flag:
        return flag_image(content)

    elif prediction_type == PredictionType.image_orientation:
        return find_image_orientation(content)

    elif prediction_type == PredictionType.product_weight:
        return find_product_weight(content)

    elif prediction_type == PredictionType.trace:
        return find_traces(content)

    elif prediction_type == PredictionType.nutrient:
        return find_nutrient_values(content)

    elif prediction_type == PredictionType.nutrient_mention:
        return find_nutrient_mentions(content)

    elif prediction_type == PredictionType.brand:
        return find_brands(content)

    elif prediction_type == PredictionType.store:
        return find_stores(content)

    elif prediction_type == PredictionType.packaging:
        return find_packaging(content)

    elif prediction_type == PredictionType.location:
        return find_locations(content)

    elif prediction_type == PredictionType.image_lang:
        return get_image_lang(content)

    elif prediction_type == PredictionType.category:
        # TODO: This has been temporarily commented-out as this breaks OCR detection
        # due to the model not being fully integrated with Robotoff.
        # return predict_ocr_categories(content)
        logger.info(
            "Skipping category OCR prediction until it has been integrated into Robotoff"
        )
        return []

    else:
        raise ValueError("unknown prediction type: {}".format(prediction_type))


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


def ocr_content_iter(items: Iterable[JSONType]) -> Iterable[Tuple[Optional[str], Dict]]:
    for item in items:
        if "content" in item:
            source = item["source"].replace("//", "/").replace(".json", ".jpg")
            yield source, item["content"]


def ocr_iter(
    source: Union[str, TextIO, pathlib.Path]
) -> Iterable[Tuple[Optional[str], Dict]]:
    if isinstance(source, pathlib.Path):
        items = jsonl_iter(source)
        yield from ocr_content_iter(items)

    elif not isinstance(source, str):
        items = jsonl_iter_fp(source)
        yield from ocr_content_iter(items)

    elif is_barcode(source):
        barcode: str = source
        image_data = fetch_images_for_ean(source)["product"]["images"]

        for image_id in image_data.keys():
            if image_id.isdigit():
                print("Getting OCR for image {}".format(image_id))
                data = get_json_for_image(barcode, image_id)
                source = get_source(image_id, barcode=barcode)
                if data:
                    yield source, data

    else:
        input_path = pathlib.Path(source)

        if not input_path.exists():
            print("Unrecognized input: {}".format(input_path))
            return

        if input_path.is_dir():
            for json_path in input_path.glob("**/*.json"):
                with open(str(json_path), "rb") as f:
                    source = get_source(json_path.stem, json_path=str(json_path))
                    yield source, orjson.loads(f.read())
        else:
            if ".json" in input_path.suffixes:
                with open(str(input_path), "rb") as f:
                    yield None, orjson.loads(f.read())

            elif ".jsonl" in input_path.suffixes:
                items = jsonl_iter(input_path)
                yield from ocr_content_iter(items)
