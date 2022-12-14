import datetime
from typing import Iterable, Optional

from PIL import Image

from robotoff.models import ImageModel, ImagePrediction
from robotoff.off import get_source_from_url
from robotoff.prediction import ocr
from robotoff.prediction.object_detection import (
    OBJECT_DETECTION_MODEL_VERSION,
    ObjectDetectionModelRegistry,
)
from robotoff.prediction.ocr.core import get_ocr_result
from robotoff.prediction.types import Prediction
from robotoff.types import ObjectDetectionModel, PredictionType
from robotoff.utils import get_logger, http_session

logger = get_logger(__name__)


DEFAULT_OCR_PREDICTION_TYPES: list[PredictionType] = [
    PredictionType.category,
    PredictionType.label,
    PredictionType.packager_code,
    PredictionType.product_weight,
    PredictionType.image_flag,
    PredictionType.expiration_date,
    PredictionType.brand,
    PredictionType.store,
    PredictionType.nutrient,
    PredictionType.nutrient_mention,
    PredictionType.image_lang,
    PredictionType.image_orientation,
]


PRODUCT_NAME_PREDICTION_TYPES: list[PredictionType] = [
    PredictionType.label,
    PredictionType.product_weight,
    PredictionType.brand,
]


def run_object_detection_model(
    model_name: ObjectDetectionModel,
    image: Image.Image,
    source_image: str,
    threshold: float = 0.1,
) -> Optional[ImagePrediction]:
    """Run a model detection model and save the results in the
    `image_prediction` table.

    An item with the corresponding `source_image` in the `image` table is
    expected to exist. Nothing is done if an image prediction already exists
    in DB for this image and model.

    :param model_name: name of the object detection model to use
    :param image: the input Pillow image
    :param source_image: the source image path (used to fetch the image from
      `image` table)
    :param threshold: the minimum object score above which we keep the object data

    :return: return None if the image does not exist in DB, or the created
      `ImagePrediction` otherwise
    """
    image_instance = ImageModel.get_or_none(source_image=source_image)

    if image_instance is None:
        logger.warning("Missing image in DB for image %s", source_image)
        return None

    existing_image_prediction = ImagePrediction.get_or_none(
        image=image_instance, model_name=model_name.value
    )
    if existing_image_prediction is not None:
        logger.info(
            f"Object detection results for {model_name} already exist for "
            f"image {source_image}: ID {existing_image_prediction.id}"
        )
        return None

    timestamp = datetime.datetime.utcnow()
    results = ObjectDetectionModelRegistry.get(model_name.value).detect_from_image(
        image, output_image=False
    )
    data = results.to_json(threshold=threshold)
    max_confidence = max([item["score"] for item in data], default=None)
    return ImagePrediction.create(
        image=image_instance,
        type="object_detection",
        model_name=model_name.value,
        model_version=OBJECT_DETECTION_MODEL_VERSION[model_name],
        data={"objects": data},
        timestamp=timestamp,
        max_confidence=max_confidence,
    )


def get_predictions_from_product_name(
    barcode: str, product_name: str
) -> list[Prediction]:
    predictions_all = []
    for prediction_type in PRODUCT_NAME_PREDICTION_TYPES:
        predictions = ocr.extract_predictions(
            product_name, prediction_type, barcode=barcode
        )
        for prediction in predictions:
            prediction.data["source"] = "product_name"
            # Predictions from product name are not as trustworthy as
            # predictions from OCR, so disable automatic processing
            prediction.automatic_processing = False
        predictions_all += predictions

    return predictions_all


def extract_ocr_predictions(
    barcode: str, ocr_url: str, prediction_types: Iterable[PredictionType]
) -> list[Prediction]:
    logger.info("Generating OCR predictions from OCR %s", ocr_url)

    predictions_all: list[Prediction] = []
    source_image = get_source_from_url(ocr_url)
    ocr_result = get_ocr_result(ocr_url, http_session, error_raise=False)

    if ocr_result is None:
        return predictions_all

    for prediction_type in prediction_types:
        predictions_all += ocr.extract_predictions(
            ocr_result, prediction_type, barcode=barcode, source_image=source_image
        )

    return predictions_all
