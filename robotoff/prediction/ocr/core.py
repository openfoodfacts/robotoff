import pathlib
from typing import Callable, Iterable, Optional, TextIO, Union

from openfoodfacts.ocr import OCRResult

from robotoff.types import JSONType, Prediction, PredictionType, ProductIdentifier
from robotoff.utils import get_logger, jsonl_iter, jsonl_iter_fp

from .brand import find_brands
from .category import find_category
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


def extract_predictions(
    content: Union[OCRResult, str],
    prediction_type: PredictionType,
    product_id: Optional[ProductIdentifier] = None,
    source_image: Optional[str] = None,
) -> list[Prediction]:
    """Extract predictions from OCR using for provided prediction type.

    :param content: OCR output to extract predictions from.
    :param prediction_type: type of the prediction to extract.
    :param product_id: identifier of the product (barcode + server type) to
        add to each prediction, defaults to None.
    :param source_image: `source_image`to add to each prediction, defaults to
        None.
    :return: The generated predictions.
    """
    if prediction_type in PREDICTION_TYPE_TO_FUNC:
        predictions = PREDICTION_TYPE_TO_FUNC[prediction_type](content)
        for prediction in predictions:
            prediction.source_image = source_image
            if product_id is not None:
                prediction.barcode = product_id.barcode
                prediction.server_type = product_id.server_type

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
