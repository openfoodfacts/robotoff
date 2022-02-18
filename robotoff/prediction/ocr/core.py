import json
import pathlib
from typing import Callable, Dict, Iterable, List, Optional, TextIO, Tuple, Union

import orjson
import requests

from robotoff.off import generate_json_ocr_url, get_barcode_from_path, split_barcode
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.settings import BaseURLProvider
from robotoff.utils import get_logger, http_session, jsonl_iter, jsonl_iter_fp
from robotoff.utils.types import JSONType

from .brand import find_brands
from .dataclass import OCRParsingException, OCRResult, OCRResultGenerationException
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


PREDICTION_TYPE_TO_FUNC: Dict[
    str, Callable[[Union[OCRResult, str]], List[Prediction]]
] = {
    PredictionType.packager_code: find_packager_codes,
    PredictionType.label: find_labels,
    PredictionType.expiration_date: find_expiration_date,
    PredictionType.image_flag: flag_image,
    PredictionType.image_orientation: find_image_orientation,
    PredictionType.product_weight: find_product_weight,
    PredictionType.trace: find_traces,
    PredictionType.nutrient: find_nutrient_values,
    PredictionType.nutrient_mention: find_nutrient_mentions,
    PredictionType.brand: find_brands,
    PredictionType.store: find_stores,
    PredictionType.packaging: find_packaging,
    PredictionType.location: find_locations,
    PredictionType.image_lang: get_image_lang,
}


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


def get_ocr_result(
    ocr_url: str, session: requests.Session, error_raise: bool = True
) -> Optional[OCRResult]:
    try:
        r = session.get(ocr_url)
    except requests.exceptions.RequestException as e:
        error_message = f"HTTP Error when fetching OCR URL {ocr_url}"
        if error_raise:
            raise OCRResultGenerationException(error_message) from e

        logger.warning(error_message, exc_info=e)
        return None

    try:
        ocr_data: Dict = r.json()
    except json.JSONDecodeError as e:
        error_message = f"Error while decoding OCR JSON from {ocr_url}"
        if error_raise:
            raise OCRResultGenerationException(error_message) from e

        logger.warning(error_message, exc_info=e)
        return None

    try:
        return OCRResult.from_json(ocr_data)
    except OCRParsingException as e:
        if error_raise:
            raise OCRResultGenerationException(str(e)) from e

        logger.warning(f"Error while parsing OCR JSON from {ocr_url}", exc_info=e)
        return None


def extract_predictions(
    content: Union[OCRResult, str],
    prediction_type: PredictionType,
    barcode: Optional[str] = None,
    source_image: Optional[str] = None,
) -> List[Prediction]:
    """Extract predictions from OCR using for provided prediction type.

    :param content: OCR output to extract predictions from.
    :param barcode: Barcode to add to each prediction, defaults to None.
    :param source_image: `source_image`to add to each prediction, defaults to
    None.
    :return: The generated predictions.
    """
    if prediction_type in PREDICTION_TYPE_TO_FUNC:
        predictions = PREDICTION_TYPE_TO_FUNC[prediction_type](content)
        for prediction in predictions:
            prediction.barcode = barcode
            prediction.source_image = source_image
        return predictions
    else:
        raise ValueError(f"unknown prediction type: {prediction_type}")


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
