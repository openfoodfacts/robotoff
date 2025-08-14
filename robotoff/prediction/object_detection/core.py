import dataclasses
import logging
import time
from typing import Literal

import numpy as np
from openfoodfacts.ml.object_detection import ObjectDetectionRawResult, ObjectDetector
from openfoodfacts.ml.utils import resize_image
from PIL import Image
from pydantic import BaseModel, Field
from tritonclient.grpc import service_pb2

from robotoff import settings
from robotoff.prediction.object_detection.utils import visualization_utils as vis_util
from robotoff.triton import get_triton_inference_stub
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
        ..., description="The name of the model on Triton Inference Server"
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
    backend: Literal["tf", "yolo"] = Field(
        ...,
        description="The backend used by the model. It can be either `tf` for "
        "Tensorflow models or `yolo` for Ultralytics models. Tensorflow models "
        "are deprecated and should be replaced by Ultralytics models.",
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
        backend="yolo",
    ),
    ObjectDetectionModel.nutrition_table: ModelConfig(
        model_name=ObjectDetectionModel.nutrition_table.name,
        model_version="yolo-nutrition-table-1.0",
        triton_version="1",
        triton_model_name="nutrition_table",
        image_size=640,
        label_names=["nutrition-table"],
        backend="yolo",
    ),
    ObjectDetectionModel.universal_logo_detector: ModelConfig(
        model_name=ObjectDetectionModel.universal_logo_detector.name,
        model_version="tf-universal-logo-detector-1.0",
        triton_version="1",
        triton_model_name="universal_logo_detector",
        image_size=1024,
        label_names=["NULL", "brand", "label"],
        backend="tf",
    ),
    ObjectDetectionModel.price_tag_detection: ModelConfig(
        model_name=ObjectDetectionModel.price_tag_detection.name,
        model_version="price-tag-detection-1.0",
        triton_version="1",
        triton_model_name="price_tag_detection",
        image_size=960,
        label_names=["price-tag"],
        backend="yolo",
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
    )
    image_with_boxes = Image.fromarray(image_array)
    result.boxed_image = image_with_boxes


class RemoteModel:
    def __init__(self, config: ModelConfig):
        self.config = config

    def detect_from_image_tf(
        self,
        image: Image.Image,
        triton_uri: str | None = None,
        threshold: float = 0.5,
    ) -> ObjectDetectionResult:
        """Run A Tensorflow object detection model on an image.

        The model must have been trained with the Tensorflow Object Detection
        API.

        :param image: the input Pillow image
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :threshold: the minimum score for a detection to be considered,
            defaults to 0.5.
        :return: the detection result
        """
        start_time = time.monotonic()
        # Tensorflow object detection models expect an image with dimensions
        # up to 1024x1024
        resized_image = resize_image(image, (1024, 1024))
        image_array = convert_image_to_array(resized_image).astype(np.uint8)
        request = service_pb2.ModelInferRequest()
        request.model_name = self.config.triton_model_name

        image_input = service_pb2.ModelInferRequest().InferInputTensor()
        image_input.name = "inputs"
        image_input.datatype = "UINT8"
        image_input.shape.extend([1, image_array.shape[0], image_array.shape[1], 3])
        request.inputs.extend([image_input])

        for output_name in (
            "num_detections",
            "detection_classes",
            "detection_scores",
            "detection_boxes",
        ):
            output = service_pb2.ModelInferRequest().InferRequestedOutputTensor()
            output.name = output_name
            request.outputs.extend([output])
        request.raw_input_contents.extend([image_array.tobytes()])
        ml_metrics_logger.info(
            "Preprocessing time for %s: %ss",
            self.config.triton_model_name,
            time.monotonic() - start_time,
        )

        start_time = time.monotonic()
        grpc_stub = get_triton_inference_stub(triton_uri)
        response = grpc_stub.ModelInfer(request)
        ml_metrics_logger.info(
            "Inference time for %s: %ss",
            self.config.triton_model_name,
            time.monotonic() - start_time,
        )

        start_time = time.monotonic()
        if len(response.outputs) != 4:
            raise Exception(f"expected 4 output, got {len(response.outputs)}")

        if len(response.raw_output_contents) != 4:
            raise Exception(
                f"expected 4 raw output content, got {len(response.raw_output_contents)}"
            )

        output_index = {output.name: i for i, output in enumerate(response.outputs)}
        detection_scores = np.frombuffer(
            response.raw_output_contents[output_index["detection_scores"]],
            dtype=np.float32,
        ).reshape((1, -1))[0]
        detection_classes = (
            np.frombuffer(
                response.raw_output_contents[output_index["detection_classes"]],
                dtype=np.float32,
            )
            .reshape((1, -1))
            .astype(int)
        )[0]
        detection_boxes = np.frombuffer(
            response.raw_output_contents[output_index["detection_boxes"]],
            dtype=np.float32,
        ).reshape((1, -1, 4))[0]

        threshold_mask = detection_scores > threshold
        detection_scores = detection_scores[threshold_mask]
        detection_boxes = detection_boxes[threshold_mask]
        detection_classes = detection_classes[threshold_mask]

        result = ObjectDetectionResult(
            num_detections=len(detection_scores),
            detection_classes=detection_classes,
            detection_boxes=detection_boxes,
            detection_scores=detection_scores,
            label_names=self.config.label_names,
        )
        ml_metrics_logger.info(
            "Post-processing time for %s: %ss",
            self.config.triton_model_name,
            time.monotonic() - start_time,
        )
        return result

    def detect_from_image_yolo(
        self,
        image: Image.Image,
        triton_uri: str | None = None,
        threshold: float = 0.5,
    ) -> ObjectDetectionResult:
        """Run an object detection model on an image.

        The model must have been trained with Ultralytics library.

        :param image: the input Pillow image
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :threshold: the minimum score for a detection to be considered,
            defaults to 0.5.
        :return: the detection result
        """
        triton_uri = triton_uri or settings.DEFAULT_TRITON_URI
        start_time = time.monotonic()
        result = ObjectDetector(
            model_name=self.config.triton_model_name,
            label_names=self.config.label_names,
            image_size=self.config.image_size,
        ).detect_from_image(image=image, triton_uri=triton_uri, threshold=threshold)
        ml_metrics_logger.info(
            "Total inference time for %s: %ss",
            self.config.triton_model_name,
            time.monotonic() - start_time,
        )
        return ObjectDetectionResult(**dataclasses.asdict(result))

    def detect_from_image(
        self,
        image: Image.Image,
        output_image: bool = False,
        triton_uri: str | None = None,
        threshold: float = 0.5,
    ) -> ObjectDetectionResult:
        """Run an object detection model on an image.

        :param image: the input Pillow image
        :param output_image: if True, the image with boxes and labels is
            returned in the result
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :threshold: the minimum score for a detection to be considered.
        :return: the detection result
        """
        if self.config.backend == "tf":
            result = self.detect_from_image_tf(image, triton_uri, threshold)

        elif self.config.backend == "yolo":
            result = self.detect_from_image_yolo(
                image=image, triton_uri=triton_uri, threshold=threshold
            )
        else:
            raise ValueError(f"Unknown backend: {self.config.backend}")

        if output_image:
            add_boxes_and_labels(
                convert_image_to_array(image).astype(np.uint8),
                result,
            )
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
