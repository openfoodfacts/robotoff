import dataclasses
import logging

import numpy as np
import sentry_sdk
from openfoodfacts.ml.object_detection import ObjectDetectionRawResult, ObjectDetector
from PIL import Image
from pydantic import BaseModel, Field

from robotoff import settings
from robotoff.prediction.object_detection.utils import visualization_utils as vis_util
from robotoff.types import ObjectDetectionModel
from robotoff.utils.image import convert_image_to_array

ml_metrics_logger = logging.getLogger("robotoff.ml_metrics")


class ModelConfig(BaseModel):
    """Configuration of an object detection model."""

    model_name: str = Field(
        ...,
        description="The name of the model, it will be used as "
        "`model_name` field in `image_prediction` table",
    )
    model_version: str = Field(
        ...,
        description="The version of the model, it will be used as "
        "`model_version` field in `image_prediction` table",
    )
    triton_version: str = Field(
        ...,
        description="The version of the model used on Triton Inference Server (eg: `1`)",
    )
    triton_model_name: str = Field(
        ...,
        description="The name of the model on Triton Inference Server. It should match "
        "the name of the model repository in models/triton/*.",
    )
    image_size: int = Field(
        ...,
        description="The size of the image expected by the model. "
        "The original image will be resized to this size.",
    )
    label_names: list[str] = Field(
        ...,
        description="The names of the labels used by the model. "
        "The order of the labels must match the order of the classes in the model.",
    )
    default_threshold: float = Field(
        default=0.5,
        description="The default detection threshold to use for the model.",
    )


MODELS_CONFIG = {
    ObjectDetectionModel.nutriscore: ModelConfig(
        model_name=ObjectDetectionModel.nutriscore.name,
        model_version="yolo-nutriscore-1.0",
        triton_version="1",
        triton_model_name="nutriscore",
        image_size=640,
        label_names=[
            "nutriscore-a",
            "nutriscore-b",
            "nutriscore-c",
            "nutriscore-d",
            "nutriscore-e",
        ],
    ),
    ObjectDetectionModel.nutrition_table: ModelConfig(
        model_name=ObjectDetectionModel.nutrition_table.name,
        model_version="yolo-nutrition-table-1.0",
        triton_version="1",
        triton_model_name="nutrition_table",
        image_size=640,
        label_names=["nutrition-table"],
    ),
    ObjectDetectionModel.universal_logo_detector: ModelConfig(
        model_name=ObjectDetectionModel.universal_logo_detector.name,
        model_version="yolo-universal-logo-detector-1.0",
        triton_version="1",
        triton_model_name="universal_logo_detector_yolo",
        image_size=640,
        label_names=["object"],
        default_threshold=0.25,
    ),
    ObjectDetectionModel.price_tag_detection: ModelConfig(
        model_name=ObjectDetectionModel.price_tag_detection.name,
        model_version="price-tag-detection-1.0",
        triton_version="1",
        triton_model_name="price_tag_detection",
        image_size=960,
        label_names=["price-tag"],
        default_threshold=0.25,
    ),
}


class ObjectDetectionResult(ObjectDetectionRawResult):
    boxed_image: Image.Image | None


def add_boxes_and_labels(image_array: np.ndarray, result: ObjectDetectionResult):
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_array,
        result.detection_boxes,
        result.detection_classes,
        result.detection_scores,
        result.label_names,
        instance_masks=None,
        use_normalized_coordinates=True,
        line_thickness=5,
        max_boxes_to_draw=len(result.detection_boxes),
        min_score_thresh=0.0,
    )
    image_with_boxes = Image.fromarray(image_array)
    result.boxed_image = image_with_boxes


class RemoteModel:
    def __init__(self, config: ModelConfig):
        self.config = config

    def detect_from_image(
        self,
        image: np.ndarray,
        output_image: bool = False,
        triton_uri: str | None = None,
        threshold: float | None = None,
        nms_threshold: float | None = None,
        nms_eta: float | None = None,
        nms: bool = True,
    ) -> ObjectDetectionResult:
        """Run an object detection model on an image.

        The model must have been trained with Ultralytics library.

        :param image: the input image, a numpy uint8 array with
            shape (height, width, 3) and RGB channels)
        :param output_image: if True, the image with boxes and labels is
            returned in the result
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :threshold: the minimum score for a detection to be considered,
            defaults to config.default_threshold.
        :param nms_threshold: the NMS (Non Maximum Suppression) threshold to use,
            defaults to None (0.7 will be used).
        :param nms_eta: the NMS eta parameter to use, defaults to None (1.0 will be
            used).
        :param nms: whether to use NMS, defaults to True.
        :return: the detection result
        """
        threshold = threshold or self.config.default_threshold
        triton_uri = triton_uri or settings.DEFAULT_TRITON_URI
        result = ObjectDetector(
            model_name=self.config.triton_model_name,
            label_names=self.config.label_names,
            image_size=self.config.image_size,
        ).detect_from_image(
            image=image,
            triton_uri=triton_uri,
            threshold=threshold,
            nms_threshold=nms_threshold,
            nms_eta=nms_eta,
            nms=nms,
        )
        for metric_name, duration in result.metrics.items():
            ml_metrics_logger.info(
                "timer: %s - %s: %sms",
                self.config.triton_model_name,
                metric_name,
                duration * 1000,
            )
            sentry_sdk.metrics.distribution(
                f"ml.object_detection.{metric_name}",
                duration * 1000,
                unit="ms",
                attributes={"model": self.config.triton_model_name},
            )

        result = ObjectDetectionResult(**dataclasses.asdict(result))

        if output_image:
            if isinstance(image, Image.Image):
                output_image_array = convert_image_to_array(image).astype(np.uint8)
            else:
                output_image_array = image.copy()

            add_boxes_and_labels(output_image_array, result)
        return result


class ObjectDetectionModelRegistry:
    models: dict[ObjectDetectionModel, RemoteModel] = {}
    _loaded = False

    @classmethod
    def load_all(cls):
        if cls._loaded:
            return
        for model, config in MODELS_CONFIG.items():
            cls.models[model] = cls.load(model, config)
        cls._loaded = True

    @classmethod
    def load(cls, model: ObjectDetectionModel, config: ModelConfig) -> RemoteModel:
        remote_model = RemoteModel(config)
        cls.models[model] = remote_model
        return remote_model

    @classmethod
    def get(cls, model: ObjectDetectionModel) -> RemoteModel:
        cls.load_all()
        return cls.models[model]
