import datetime
from typing import Iterable

from openfoodfacts.ocr import OCRResult
from PIL import Image

from robotoff.models import ImageModel, ImagePrediction
from robotoff.off import get_source_from_url
from robotoff.prediction import ocr
from robotoff.prediction.object_detection import (
    MODELS_CONFIG,
    ObjectDetectionModelRegistry,
)
from robotoff.types import (
    ObjectDetectionModel,
    Prediction,
    PredictionType,
    ProductIdentifier,
)
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
    PredictionType.packaging,
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
    image_model: ImageModel,
    threshold: float = 0.1,
    return_null_if_exist: bool = True,
    triton_uri: str | None = None,
) -> ImagePrediction | None:
    """Run a model detection model and save the results in the
    `image_prediction` table.

    An item with the corresponding `source_image` in the `image` table is
    expected to exist. Nothing is done if an image prediction already exists in
    DB for this image and model.

    :param model_name: name of the object detection model to use
    :param image: the input Pillow image
    :param image_model: the image in DB
    :param source_image: the source image path (used to fetch the image from
      `image` table)
    :param threshold: the minimum object score above which we keep the object
        data
    :param return_null_if_exist: if True, return None if the image prediction
        already exists in DB
    :param triton_uri: URI of the Triton Inference Server, defaults to
        None. If not provided, the default value from settings is used.
    :return: return None if the image does not exist in DB, or the created
      `ImagePrediction` otherwise
    """
    if (
        existing_image_prediction := ImagePrediction.get_or_none(
            image=image_model, model_name=model_name.name
        )
    ) is not None:
        if return_null_if_exist:
            return None
        return existing_image_prediction

    timestamp = datetime.datetime.now(datetime.timezone.utc)
    results = ObjectDetectionModelRegistry.get(model_name).detect_from_image(
        image, output_image=False, triton_uri=triton_uri, threshold=threshold
    )
    data = results.to_list()
    max_confidence = max((item["score"] for item in data), default=None)
    return ImagePrediction.create(
        image=image_model,
        type="object_detection",
        model_name=model_name.name,
        model_version=MODELS_CONFIG[model_name].model_version,
        data={"objects": data},
        timestamp=timestamp,
        max_confidence=max_confidence,
    )


def get_predictions_from_product_name(
    product_id: ProductIdentifier, product_name: str
) -> list[Prediction]:
    predictions_all = []
    for prediction_type in PRODUCT_NAME_PREDICTION_TYPES:
        predictions = ocr.extract_predictions(
            product_name, prediction_type, product_id=product_id
        )
        for prediction in predictions:
            prediction.data["source"] = "product_name"
            # Predictions from product name are not as trustworthy as
            # predictions from OCR, so disable automatic processing
            prediction.automatic_processing = False
        predictions_all += predictions

    return predictions_all


def extract_ocr_predictions(
    product_id: ProductIdentifier,
    ocr_url: str,
    prediction_types: Iterable[PredictionType],
) -> list[Prediction]:
    logger.info("Generating OCR predictions from OCR %s", ocr_url)

    predictions_all: list[Prediction] = []
    source_image = get_source_from_url(ocr_url)
    ocr_result = OCRResult.from_url(ocr_url, http_session, error_raise=False)

    if ocr_result is None:
        return predictions_all

    for prediction_type in prediction_types:
        predictions_all += ocr.extract_predictions(
            ocr_result,
            prediction_type,
            product_id=product_id,
            source_image=source_image,
        )

    return predictions_all
