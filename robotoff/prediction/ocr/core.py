import json
import pathlib
from typing import Callable, Iterable, Optional, TextIO, Union

import requests

from robotoff.types import JSONType, Prediction, PredictionType
from robotoff.utils import get_logger, jsonl_iter, jsonl_iter_fp

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
from .packaging import find_packaging
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
    PredictionType.packaging: find_packaging,
    PredictionType.location: find_locations,
    PredictionType.image_lang: get_image_lang,
}


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

    if not r.ok:
        logger.warning(
            "Non-200 status code (%s) when fetching OCR URL: %s", r.status_code, ocr_url
        )
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
