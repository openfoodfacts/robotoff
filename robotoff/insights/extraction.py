from typing import Dict, Iterable, List, Optional

from PIL import Image

from robotoff.off import get_source_from_url
from robotoff.prediction import ocr
from robotoff.prediction.object_detection import ObjectDetectionModelRegistry
from robotoff.prediction.ocr.core import get_ocr_result
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.utils import get_logger, http_session

logger = get_logger(__name__)


DEFAULT_OCR_PREDICTION_TYPES: List[PredictionType] = [
    PredictionType.label,
    PredictionType.packager_code,
    PredictionType.product_weight,
    PredictionType.image_flag,
    PredictionType.expiration_date,
    PredictionType.brand,
    PredictionType.store,
    PredictionType.packaging,
    PredictionType.nutrient,
    PredictionType.nutrient_mention,
    PredictionType.image_lang,
    PredictionType.image_orientation,
]


PRODUCT_NAME_PREDICTION_TYPES: List[PredictionType] = [
    PredictionType.label,
    PredictionType.product_weight,
    PredictionType.brand,
]


def get_predictions_from_product_name(
    barcode: str, product_name: str
) -> List[Prediction]:
    predictions_all = []
    for prediction_type in PRODUCT_NAME_PREDICTION_TYPES:
        predictions = ocr.extract_predictions(
            product_name, prediction_type, barcode=barcode
        )
        for prediction in predictions:
            prediction.data["source"] = "product_name"
        predictions_all += predictions

    return predictions_all


def get_predictions_from_image(
    barcode: str, image: Image.Image, source_image: str, ocr_url: str
) -> List[Prediction]:
    logger.info(f"Generating OCR predictions from OCR {ocr_url}")
    ocr_predictions = extract_ocr_predictions(
        barcode, ocr_url, DEFAULT_OCR_PREDICTION_TYPES
    )
    extract_nutriscore = any(
        prediction.value_tag == "en:nutriscore"
        and prediction.type == PredictionType.label
        for prediction in ocr_predictions
    )
    image_ml_predictions = extract_image_ml_predictions(
        barcode, image, source_image, extract_nutriscore=extract_nutriscore
    )
    return ocr_predictions + image_ml_predictions


def extract_image_ml_predictions(
    barcode: str, image: Image.Image, source_image: str, extract_nutriscore: bool = True
) -> List[Prediction]:
    if extract_nutriscore:
        # Currently all of the automatic processing for the Nutri-Score grades has been
        # disabled due to a prediction quality issue.
        # Last automatic processing threshold was set to 0.9 - resulting in ~70% incorrect
        # detection.
        nutriscore_prediction = extract_nutriscore_label(
            image,
            manual_threshold=0.5,
        )

        if nutriscore_prediction:
            nutriscore_prediction.barcode = barcode
            nutriscore_prediction.source_image = source_image
            return [nutriscore_prediction]

    return []


def extract_ocr_predictions(
    barcode: str, ocr_url: str, prediction_types: Iterable[PredictionType]
) -> List[Prediction]:
    predictions_all: List[Prediction] = []
    source_image = get_source_from_url(ocr_url)
    ocr_result = get_ocr_result(ocr_url, http_session, error_raise=False)

    if ocr_result is None:
        return predictions_all

    for prediction_type in prediction_types:
        predictions_all += ocr.extract_predictions(
            ocr_result, prediction_type, barcode=barcode, source_image=source_image
        )

    return predictions_all


NUTRISCORE_LABELS: Dict[str, str] = {
    "nutriscore-a": "en:nutriscore-grade-a",
    "nutriscore-b": "en:nutriscore-grade-b",
    "nutriscore-c": "en:nutriscore-grade-c",
    "nutriscore-d": "en:nutriscore-grade-d",
    "nutriscore-e": "en:nutriscore-grade-e",
}


def extract_nutriscore_label(
    image: Image.Image,
    manual_threshold: float,
    automatic_threshold: Optional[float] = None,
) -> Optional[Prediction]:
    model = ObjectDetectionModelRegistry.get("nutriscore")
    raw_result = model.detect_from_image(image, output_image=False)
    results = raw_result.select(threshold=manual_threshold)

    if not results:
        return None

    if len(results) > 1:
        logger.warning("more than one nutriscore detected, discarding detections")
        return None

    result = results[0]
    score = result.score

    automatic_processing = False
    if automatic_threshold:
        automatic_processing = score >= automatic_threshold
    label_tag = NUTRISCORE_LABELS[result.label]

    return Prediction(
        type=PredictionType.label,
        value_tag=label_tag,
        automatic_processing=automatic_processing,
        data={
            "confidence": score,
            "bounding_box": result.bounding_box,
            "model": "nutriscore",
            "notify": True,
        },
    )
