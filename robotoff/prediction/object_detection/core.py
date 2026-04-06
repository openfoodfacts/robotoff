import dataclasses
import logging
import time

import numpy as np
import sentry_sdk
from openfoodfacts.ml.object_detection import (
    ObjectDetectionRawResult,
    ObjectDetector,
    apply_nms,
    object_detection_transform,
)
from PIL import Image
from pydantic import BaseModel, Field

from robotoff import settings
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
    from robotoff.prediction.object_detection.utils import (
        visualization_utils as vis_util,
    )

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


class OptimizedObjectDetector(ObjectDetector):
    """Robotoff-specific wrapper around ObjectDetector hot paths.

    The upstream implementation still performs post-processing with a Python loop
    over every candidate detection. We keep the same output format and NMS
    behavior, but we vectorize the class/score/bounding-box extraction.
    """

    def __init__(self, model_name: str, label_names: list[str], image_size: int = 640):
        super().__init__(model_name, label_names, image_size=image_size)
        self._transform = object_detection_transform(image_size=image_size)

    def preprocess(self, image_array: np.ndarray) -> np.ndarray:
        image_array = self._transform(image=image_array)["image"]
        return np.transpose(image_array, (2, 0, 1))[np.newaxis, :]

    @staticmethod
    def _reverse_bboxes_transform(
        y_min: np.ndarray,
        x_min: np.ndarray,
        y_max: np.ndarray,
        x_max: np.ndarray,
        original_shape: tuple[int, int],
        image_size: int,
    ) -> np.ndarray:
        original_h, original_w = original_shape
        scale = image_size / max(original_h, original_w)
        scaled_h = int(original_h * scale)
        scaled_w = int(original_w * scale)
        pad_top = (image_size - scaled_h) // 2
        pad_left = (image_size - scaled_w) // 2

        detection_boxes = np.empty((len(y_min), 4), dtype=np.float32)
        detection_boxes[:, 0] = np.clip(
            ((y_min - pad_top) / scale) / original_h, 0.0, 1.0
        )
        detection_boxes[:, 1] = np.clip(
            ((x_min - pad_left) / scale) / original_w, 0.0, 1.0
        )
        detection_boxes[:, 2] = np.clip(
            ((y_max - pad_top) / scale) / original_h, 0.0, 1.0
        )
        detection_boxes[:, 3] = np.clip(
            ((x_max - pad_left) / scale) / original_w, 0.0, 1.0
        )
        return detection_boxes

    def postprocess(
        self,
        response,
        threshold: float,
        original_shape: tuple[int, int],
        nms_threshold: float | None = None,
        nms_eta: float | None = None,
        nms: bool = True,
    ) -> ObjectDetectionRawResult:
        if len(response.outputs) != 1:
            raise ValueError(f"expected 1 output, got {len(response.outputs)}")

        if len(response.raw_output_contents) != 1:
            raise ValueError(
                "expected 1 raw output content, got "
                f"{len(response.raw_output_contents)}"
            )

        if nms_threshold is None:
            nms_threshold = 0.7
        if nms_eta is None:
            nms_eta = 1.0

        output_index = {output.name: i for i, output in enumerate(response.outputs)}
        output = np.frombuffer(
            response.raw_output_contents[output_index["output0"]],
            dtype=np.float32,
        ).reshape((1, len(self.label_names) + 4, -1))[0]

        rows = output.shape[1]
        class_scores = output[4:, :]
        raw_detection_classes = np.argmax(class_scores, axis=0).astype(int)
        raw_detection_scores = np.max(class_scores, axis=0).astype(np.float32)
        keep = raw_detection_scores >= threshold

        raw_detection_classes = raw_detection_classes[keep]
        raw_detection_scores = raw_detection_scores[keep]

        box_data = output[:4, keep]
        bbox_width = box_data[2]
        bbox_height = box_data[3]
        x_min = box_data[0] - 0.5 * bbox_width
        y_min = box_data[1] - 0.5 * bbox_height
        x_max = x_min + bbox_width
        y_max = y_min + bbox_height

        raw_detection_boxes = self._reverse_bboxes_transform(
            y_min=y_min,
            x_min=x_min,
            y_max=y_max,
            x_max=x_max,
            original_shape=original_shape,
            image_size=self.image_size,
        )

        metrics: dict[str, float] = {}
        if nms:
            start_time = time.monotonic()
            detection_boxes, detection_scores, detection_classes = apply_nms(
                bboxes=raw_detection_boxes,
                scores=raw_detection_scores,
                classes=raw_detection_classes,
                threshold=threshold,
                nms_threshold=nms_threshold,
                nms_eta=nms_eta,
            )
            metrics["postprocess_nms_time"] = time.monotonic() - start_time
        else:
            detection_boxes = raw_detection_boxes
            detection_scores = raw_detection_scores
            detection_classes = raw_detection_classes

        return ObjectDetectionRawResult(
            num_detections=rows,
            detection_classes=detection_classes,
            detection_boxes=detection_boxes,
            detection_scores=detection_scores,
            label_names=self.label_names,
            metrics=metrics,
        )


class RemoteModel:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.detector = OptimizedObjectDetector(
            model_name=config.triton_model_name,
            label_names=config.label_names,
            image_size=config.image_size,
        )

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
        result = self.detector.detect_from_image(
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
