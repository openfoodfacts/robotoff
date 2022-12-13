import json
import pathlib
from typing import Callable, Iterable, Optional, TextIO, Union

import requests

from robotoff.off import generate_json_ocr_url, get_barcode_from_path, split_barcode
from robotoff.prediction.types import Prediction
from robotoff.settings import BaseURLProvider
from robotoff.types import PredictionType
from robotoff.utils import get_logger, http_session, jsonl_iter, jsonl_iter_fp
from robotoff.utils.types import JSONType

from .brand import find_brands
from .category import find_category
from .dataclass import OCRParsingException, OCRResult, OCRResultGenerationException
from .expiration_date import find_expiration_date
from .image_flag import flag_image
from .image_lang import get_image_lang
from .image_orientation import find_image_orientation
from .label import find_labels
from .location import find_locations
from .nutrient import find_nutrient_mentions, find_nutrient_values
from .packager_code import find_packager_codes
from .product_weight import find_product_weight
from .store import find_stores
from .trace import find_traces

logger = get_logger(__name__)


PREDICTION_TYPE_TO_FUNC: dict[
    str, Callable[[Union[OCRResult, str]], list[Prediction]]
] = {
    PredictionType.category: find_category,
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
        error_message = "HTTP Error when fetching OCR URL"
        if error_raise:
            raise OCRResultGenerationException(error_message, ocr_url) from e

        logger.warning(error_message + ": %s", ocr_url, exc_info=e)
        return None

    try:
        ocr_data: dict = r.json()
    except json.JSONDecodeError as e:
        error_message = "Error while decoding OCR JSON"
        if error_raise:
            raise OCRResultGenerationException(error_message, ocr_url) from e

        logger.warning(error_message + ": %s", ocr_url, exc_info=e)
        return None

    try:
        return OCRResult.from_json(ocr_data)
    except OCRParsingException as e:
        if error_raise:
            raise OCRResultGenerationException(str(e), ocr_url) from e

        logger.warning("Error while parsing OCR JSON from %s", ocr_url, exc_info=e)
        return None


def extract_predictions(
    content: Union[OCRResult, str],
    prediction_type: PredictionType,
    barcode: Optional[str] = None,
    source_image: Optional[str] = None,
) -> list[Prediction]:
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
    image_name: str, json_path: Optional[str] = None, barcode: Optional[str] = None
) -> str:
    if not barcode:
        barcode = get_barcode_from_path(str(json_path))

        if not barcode:
            raise ValueError("invalid JSON path: {}".format(json_path))

    return "/{}/{}.jpg" "".format("/".join(split_barcode(barcode)), image_name)


def ocr_content_iter(items: Iterable[JSONType]) -> Iterable[tuple[Optional[str], dict]]:
    for item in items:
        if "content" in item:
            source = item["source"].replace("//", "/").replace(".json", ".jpg")
            yield source, item["content"]


def ocr_iter(
    source: Union[str, TextIO, pathlib.Path]
) -> Iterable[tuple[Optional[str], dict]]:
    if isinstance(source, pathlib.Path):
        items = jsonl_iter(source)
        yield from ocr_content_iter(items)

    elif not isinstance(source, str):
        items = jsonl_iter_fp(source)
        yield from ocr_content_iter(items)
