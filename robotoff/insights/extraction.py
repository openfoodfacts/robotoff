import pathlib
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse

from PIL import Image

from robotoff.prediction import ocr
from robotoff.prediction.object_detection import ObjectDetectionModelRegistry
from robotoff.prediction.ocr.core import get_ocr_result
from robotoff.prediction.ocr.dataclass import OCRParsingException
from robotoff.prediction.types import Prediction, PredictionType, ProductPredictions
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
) -> Dict[PredictionType, ProductPredictions]:
    results = {}
    for prediction_type in PRODUCT_NAME_PREDICTION_TYPES:
        predictions = ocr.extract_predictions(product_name, prediction_type)

        if predictions:
            for prediction in predictions:
                prediction.data["source"] = "product_name"

            results[prediction_type] = ProductPredictions(
                predictions=predictions,
                barcode=barcode,
                type=prediction_type,
            )

    return results


def get_predictions_from_image(
    barcode: str, image: Image.Image, source_image: str, ocr_url: str
) -> Dict[PredictionType, ProductPredictions]:
    logger.info(f"Generating OCR predictions from OCR {ocr_url}")
    ocr_predictions = extract_ocr_predictions(
        barcode, ocr_url, DEFAULT_OCR_PREDICTION_TYPES
    )
    extract_nutriscore = any(
        prediction.value_tag == "en:nutriscore"
        for prediction in getattr(
            ocr_predictions.get(PredictionType.label), "predictions", []
        )
    )
    image_ml_predictions = extract_image_ml_predictions(
        barcode, image, source_image, extract_nutriscore=extract_nutriscore
    )

    prediction_types = set(ocr_predictions.keys()).union(image_ml_predictions.keys())

    results: Dict[PredictionType, ProductPredictions] = {}

    for prediction_type in prediction_types:
        product_predictions: List[ProductPredictions] = []

        if prediction_type in ocr_predictions:
            product_predictions.append(ocr_predictions[prediction_type])

        if prediction_type in image_ml_predictions:
            product_predictions.append(image_ml_predictions[prediction_type])

        results[prediction_type] = ProductPredictions.merge(product_predictions)

    return results


def get_source_from_image_url(image_url: str) -> str:
    image_url_path = urlparse(image_url).path

    if image_url_path.startswith("/images/products"):
        image_url_path = image_url_path[len("/images/products") :]

    return image_url_path


def get_source_from_ocr_url(ocr_url: str) -> str:
    url_path = urlparse(ocr_url).path

    if url_path.startswith("/images/products"):
        url_path = url_path[len("/images/products") :]

    if url_path.endswith(".json"):
        url_path = str(pathlib.Path(url_path).with_suffix(".jpg"))

    return url_path


def extract_image_ml_predictions(
    barcode: str, image: Image.Image, source_image: str, extract_nutriscore: bool = True
) -> Dict[PredictionType, ProductPredictions]:
    results: Dict[PredictionType, ProductPredictions] = {}

    if extract_nutriscore:
        # Currently all of the automatic processing for the Nutri-Score grades has been
        # disabled due to a prediction quality issue.
        # Last automatic processing threshold was set to 0.9 - resulting in ~70% incorrect
        # detection.
        nutriscore_prediction = extract_nutriscore_label(
            image,
            manual_threshold=0.5,
        )

        if not nutriscore_prediction:
            return results

        results[PredictionType.label] = ProductPredictions(
            predictions=[nutriscore_prediction],
            barcode=barcode,
            source_image=source_image,
            type=PredictionType.label,
        )

    return results


def extract_ocr_predictions(
    barcode: str, ocr_url: str, prediction_types: Iterable[PredictionType]
) -> Dict[PredictionType, ProductPredictions]:
    results: Dict[PredictionType, ProductPredictions] = {}
    source_image = get_source_from_ocr_url(ocr_url)
    ocr_result = get_ocr_result(ocr_url, http_session, error_raise=False)

    if ocr_result is None:
        return results

    for prediction_type in prediction_types:
        predictions = ocr.extract_predictions(ocr_result, prediction_type)

        if predictions:
            results[prediction_type] = ProductPredictions(
                barcode=barcode,
                predictions=predictions,
                source_image=source_image,
                type=prediction_type,
            )

    return results


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
