import dataclasses
import logging
import time
from typing import Literal

import numpy as np
from cv2 import dnn
from openfoodfacts.ml.object_detection import (
    ObjectDetectionRawResult,
    add_triton_infer_input_tensor,
)
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


# Copy back ObjectDetector from openfoodfacts-python, as we want to measure the time
# spent in preprocessing, inference and postprocessing.
class ObjectDetector:
    def __init__(self, model_name: str, label_names: list[str], image_size: int = 640):
        """An object detection detector based on Yolo models.

        We support models trained with Yolov8, v9, v10 and v11.

        :param model_name: the name of the model, as registered in Triton
        :param label_names: the list of label names
        :param image_size: the size of the input image for the model
        """
        self.model_name: str = model_name
        self.label_names = label_names
        self.image_size = image_size

    def detect_from_image(
        self,
        image: Image.Image,
        triton_uri: str,
        threshold: float = 0.5,
        model_version: str | None = None,
    ) -> ObjectDetectionRawResult:
        """Run an object detection model on an image.

        The model must have been trained with Ultralytics library.

        :param image: the input Pillow image
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :param threshold: the minimum score for a detection to be considered,
            defaults to 0.5.
        :param model_version: the version of the model to use, defaults to
            None (latest).
        :return: the detection result
        """
        start_time = time.monotonic()
        image_array, scale_x, scale_y = self.preprocess(image)
        request = service_pb2.ModelInferRequest()
        request.model_name = self.model_name
        if model_version:
            request.model_version = model_version
        add_triton_infer_input_tensor(
            request, name="images", data=image_array, datatype="FP32"
        )
        ml_metrics_logger.info(
            "Preprocessing time for %s: %ss",
            self.model_name,
            time.monotonic() - start_time,
        )

        start_time = time.monotonic()
        grpc_stub = get_triton_inference_stub(triton_uri)
        response = grpc_stub.ModelInfer(request)
        ml_metrics_logger.info(
            "Inference time for %s: %ss", self.model_name, time.monotonic() - start_time
        )

        start_time = time.monotonic()
        response = self.postprocess(
            response, threshold=threshold, scale_x=scale_x, scale_y=scale_y
        )
        ml_metrics_logger.info(
            "Post-processing time for %s: %ss",
            self.model_name,
            time.monotonic() - start_time,
        )
        return response

    def preprocess(self, image: Image.Image) -> tuple[np.ndarray, float, float]:
        # Yolo object detection models expect a specific image dimension
        width, height = image.size
        # Prepare a square image for inference
        max_size = max(height, width)
        # We paste the original image into a larger square image,
        # in the upper-left corner, on a black background.
        squared_image = Image.new("RGB", (max_size, max_size), color="black")
        squared_image.paste(image, (0, 0))
        resized_image = squared_image.resize((self.image_size, self.image_size))

        # As we don't process the original image but a modified version of it,
        # we need to compute the scale factor for the x and y axis.
        image_ratio = width / height
        scale_x: float
        scale_y: float
        if image_ratio < 1:  # portrait, height > width
            scale_x = self.image_size * image_ratio
            scale_y = self.image_size
        else:  # landscape, width > height
            scale_x = self.image_size
            scale_y = self.image_size / image_ratio

        # Preprocess the image and prepare blob for model
        image_array = (
            convert_image_to_array(resized_image)
            .transpose((2, 0, 1))
            .astype(np.float32)
        )
        image_array = image_array / 255.0
        image_array = np.expand_dims(image_array, axis=0)
        return image_array, scale_x, scale_y

    def postprocess(
        self, response, threshold: float, scale_x: float, scale_y: float
    ) -> ObjectDetectionRawResult:
        if len(response.outputs) != 1:
            raise ValueError(f"expected 1 output, got {len(response.outputs)}")

        if len(response.raw_output_contents) != 1:
            raise ValueError(
                f"expected 1 raw output content, got {len(response.raw_output_contents)}"
            )

        output_index = {output.name: i for i, output in enumerate(response.outputs)}
        output = np.frombuffer(
            response.raw_output_contents[output_index["output0"]],
            dtype=np.float32,
        ).reshape((1, len(self.label_names) + 4, -1))[0]

        # output is of shape (num_classes + 4, num_detections)
        rows = output.shape[1]
        raw_detection_classes = np.zeros(rows, dtype=int)
        raw_detection_scores = np.zeros(rows, dtype=np.float32)
        raw_detection_boxes = np.zeros((rows, 4), dtype=np.float32)

        for i in range(rows):
            classes_scores = output[4:, i]
            max_cls_idx = np.argmax(classes_scores)
            max_score = classes_scores[max_cls_idx]
            if max_score < threshold:
                continue
            raw_detection_classes[i] = max_cls_idx
            raw_detection_scores[i] = max_score

            # The bounding box is in the format (x, y, width, height) in
            # relative coordinates
            # x and y are the coordinates of the center of the bounding box
            bbox_width = output[2, i]
            bbox_height = output[3, i]
            x_min = output[0, i] - 0.5 * bbox_width
            y_min = output[1, i] - 0.5 * bbox_height
            x_max = x_min + bbox_width
            y_max = y_min + bbox_height

            # We save the bounding box in the format
            # (y_min, x_min, y_max, x_max) in relative coordinates
            # Scale the bounding boxes back to the original image size
            raw_detection_boxes[i, 0] = max(0.0, min(1.0, y_min / scale_y))
            raw_detection_boxes[i, 1] = max(0.0, min(1.0, x_min / scale_x))
            raw_detection_boxes[i, 2] = max(0.0, min(1.0, y_max / scale_y))
            raw_detection_boxes[i, 3] = max(0.0, min(1.0, x_max / scale_x))

        start_time = time.monotonic()
        # Perform NMS (Non Maximum Suppression)
        detection_box_indices = dnn.NMSBoxes(
            raw_detection_boxes,  # type: ignore
            raw_detection_scores,  # type: ignore
            score_threshold=threshold,
            # the following values are copied from Ultralytics settings
            nms_threshold=0.45,
            eta=0.5,
        )
        ml_metrics_logger.info(
            "NMS time for %s: %ss",
            self.model_name,
            time.monotonic() - start_time,
        )
        detection_classes = np.zeros(len(detection_box_indices), dtype=int)
        detection_scores = np.zeros(len(detection_box_indices), dtype=np.float32)
        detection_boxes = np.zeros((len(detection_box_indices), 4), dtype=np.float32)

        for i, idx in enumerate(detection_box_indices):
            detection_classes[i] = raw_detection_classes[idx]
            detection_scores[i] = raw_detection_scores[idx]
            detection_boxes[i] = raw_detection_boxes[idx]

        result = ObjectDetectionRawResult(
            num_detections=rows,
            detection_classes=detection_classes,
            detection_boxes=detection_boxes,
            detection_scores=detection_scores,
            label_names=self.label_names,
        )
        return result


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
