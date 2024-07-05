import dataclasses
import pathlib
import time
from typing import Optional

import numpy as np
from cv2 import dnn
from PIL import Image
from tritonclient.grpc import service_pb2

from robotoff import settings
from robotoff.prediction.object_detection.utils import visualization_utils as vis_util
from robotoff.triton import get_triton_inference_stub
from robotoff.types import JSONType, ObjectDetectionModel
from robotoff.utils import get_logger, text_file_iter
from robotoff.utils.image import convert_image_to_array

logger = get_logger(__name__)

LABEL_NAMES_FILENAME = "labels.txt"


OBJECT_DETECTION_MODEL_VERSION = {
    ObjectDetectionModel.nutriscore: "tf-nutriscore-1.0",
    ObjectDetectionModel.nutriscore_yolo: "yolo-nutriscore-1.0",
    ObjectDetectionModel.nutrition_table: "tf-nutrition-table-1.0",
    ObjectDetectionModel.universal_logo_detector: "tf-universal-logo-detector-1.0",
}


@dataclasses.dataclass
class ObjectDetectionRawResult:
    num_detections: int
    detection_boxes: np.ndarray
    detection_scores: np.ndarray
    detection_classes: np.ndarray
    label_names: list[str]
    detection_masks: Optional[np.ndarray] = None
    boxed_image: Optional[Image.Image] = None

    def to_json(self) -> list[JSONType]:
        """Convert the detection results to a JSON serializable format."""
        results = []
        for bounding_box, score, label in zip(
            self.detection_boxes, self.detection_scores, self.detection_classes
        ):
            label_int = int(label)
            label_str = self.label_names[label_int]
            if label_str is not None:
                result = {
                    "bounding_box": tuple(bounding_box.tolist()),  # type: ignore
                    "score": float(score),
                    "label": label_str,
                }
                results.append(result)
        return results


def add_boxes_and_labels(image_array: np.ndarray, raw_result: ObjectDetectionRawResult):
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_array,
        raw_result.detection_boxes,
        raw_result.detection_classes,
        raw_result.detection_scores,
        raw_result.label_names,
        instance_masks=raw_result.detection_masks,
        use_normalized_coordinates=True,
        line_thickness=5,
    )
    image_with_boxes = Image.fromarray(image_array)
    raw_result.boxed_image = image_with_boxes


def resize_image(image: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    """Resize an image to fit within the specified dimensions.

    :param image: the input image
    :param max_size: the maximum width and height as a tuple
    :return: the resized image, or the original image if it fits within the
        specified dimensions
    """
    width, height = image.size
    max_width, max_height = max_size

    if width > max_width or height > max_height:
        new_image = image.copy()
        new_image.thumbnail((max_width, max_height))
        return new_image

    return image


class RemoteModel:
    def __init__(self, name: str, label_names: list[str], backend: str):
        self.name: str = name
        self.label_names = label_names
        self.backend = backend

    def detect_from_image_tf(
        self,
        image: Image.Image,
        output_image: bool = False,
        triton_uri: str | None = None,
        threshold: float = 0.5,
    ) -> ObjectDetectionRawResult:
        """Run A Tensorflow object detection model on an image.

        The model must have been trained with the Tensorflow Object Detection
        API.

        :param image: the input Pillow image
        :param output_image: if True, the image with boxes and labels is
            returned in the result
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :threshold: the minimum score for a detection to be considered,
            defaults to 0.5.
        :return: the detection result
        """
        # Tensorflow object detection models expect an image with dimensions
        # up to 1024x1024
        resized_image = resize_image(image, (1024, 1024))
        image_array = convert_image_to_array(resized_image).astype(np.uint8)
        grpc_stub = get_triton_inference_stub(triton_uri)
        request = service_pb2.ModelInferRequest()
        request.model_name = self.name

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
        start_time = time.monotonic()
        response = grpc_stub.ModelInfer(request)
        logger.debug(
            "Inference time for %s: %s", self.name, time.monotonic() - start_time
        )

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
            .astype(np.int)  # type: ignore
        )[0]
        detection_boxes = np.frombuffer(
            response.raw_output_contents[output_index["detection_boxes"]],
            dtype=np.float32,
        ).reshape((1, -1, 4))[0]

        threshold_mask = detection_scores > threshold
        detection_scores = detection_scores[threshold_mask]
        detection_boxes = detection_boxes[threshold_mask]
        detection_classes = detection_classes[threshold_mask]

        result = ObjectDetectionRawResult(
            num_detections=len(detection_scores),
            detection_classes=detection_classes,
            detection_boxes=detection_boxes,
            detection_scores=detection_scores,
            detection_masks=None,
            label_names=self.label_names,
        )

        if output_image:
            add_boxes_and_labels(image_array, result)

        return result

    def detect_from_image_yolo(
        self,
        image: Image.Image,
        output_image: bool = False,
        triton_uri: str | None = None,
        threshold: float = 0.5,
    ) -> ObjectDetectionRawResult:
        """Run an object detection model on an image.

        The model must have been trained with Ultralytics library.

        :param image: the input Pillow image
        :param output_image: if True, the image with boxes and labels is
            returned in the result
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :threshold: the minimum score for a detection to be considered,
            defaults to 0.5.
        :return: the detection result
        """
        # YoloV8 object detection models expect an image with dimensions
        # up to 640x640
        height, width = image.size
        # Prepare a square image for inference
        max_size = max(height, width)
        # We paste the original image into a larger square image, as the model
        # expects a 640x640 input.
        # We paste it in the upper-left corner, on a black background.
        squared_image = Image.new("RGB", (max_size, max_size), color="black")
        squared_image.paste(image, (0, 0))
        resized_image = squared_image.resize((640, 640))

        # As we don't process the original image but a modified version of it,
        # we need to compute the scale factor for the x and y axis.
        image_ratio = width / height
        scale_x: float
        scale_y: float
        if image_ratio > 1:
            scale_x = 640 / image_ratio
            scale_y = 640
        else:
            scale_x = 640
            scale_y = 640 * image_ratio

        # Preprocess the image and prepare blob for model
        image_array = (
            convert_image_to_array(resized_image)
            .transpose((2, 0, 1))
            .astype(np.float32)
        )
        image_array = image_array / 255.0
        image_array = np.expand_dims(image_array, axis=0)

        grpc_stub = get_triton_inference_stub(triton_uri)
        request = service_pb2.ModelInferRequest()
        request.model_name = self.name

        image_input = service_pb2.ModelInferRequest().InferInputTensor()
        image_input.name = "images"

        image_input.datatype = "FP32"

        image_input.shape.extend([1, 3, 640, 640])
        request.inputs.extend([image_input])

        output = service_pb2.ModelInferRequest().InferRequestedOutputTensor()
        output.name = "output0"
        request.outputs.extend([output])

        request.raw_input_contents.extend([image_array.tobytes()])
        start_time = time.monotonic()
        response = grpc_stub.ModelInfer(request)
        latency = time.monotonic() - start_time

        logger.debug("Inference time for %s: %s", self.name, latency)

        start_time = time.monotonic()
        if len(response.outputs) != 1:
            raise Exception(f"expected 1 output, got {len(response.outputs)}")

        if len(response.raw_output_contents) != 1:
            raise Exception(
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

        # Perform NMS (Non Maximum Suppression)
        detection_box_indices = dnn.NMSBoxes(
            raw_detection_boxes,  # type: ignore
            raw_detection_scores,  # type: ignore
            score_threshold=threshold,
            # the following values are copied from Ultralytics settings
            nms_threshold=0.45,
            eta=0.5,
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
            detection_masks=None,
            label_names=self.label_names,
        )
        latency = time.monotonic() - start_time
        logger.debug("Post-processing time for %s: %s", self.name, latency)

        if output_image:
            add_boxes_and_labels(
                convert_image_to_array(image).astype(np.uint8),
                result,
            )

        return result

    def detect_from_image(
        self,
        image: Image.Image,
        output_image: bool = False,
        triton_uri: str | None = None,
        threshold: float = 0.5,
    ) -> ObjectDetectionRawResult:
        """Run an object detection model on an image.

        :param image: the input Pillow image
        :param output_image: if True, the image with boxes and labels is
            returned in the result
        :param triton_uri: URI of the Triton Inference Server, defaults to
            None. If not provided, the default value from settings is used.
        :threshold: the minimum score for a detection to be considered.
        :return: the detection result
        """
        if self.backend == "tf":
            return self.detect_from_image_tf(image, output_image, triton_uri, threshold)
        elif self.backend == "yolo":
            return self.detect_from_image_yolo(
                image, output_image, triton_uri, threshold
            )
        else:
            raise ValueError(f"Unknown backend: {self.backend}")


class ObjectDetectionModelRegistry:
    models: dict[str, RemoteModel] = {}
    _loaded = False

    @classmethod
    def get_available_models(cls) -> list[str]:
        cls.load_all()
        return list(cls.models.keys())

    @classmethod
    def load_all(cls):
        if cls._loaded:
            return
        for model in ObjectDetectionModel:
            model_name = model.value
            file_path = settings.TRITON_MODELS_DIR / model_name
            if file_path.is_dir():
                logger.info("Model %s found", model_name)
                cls.models[model_name] = cls.load(model_name, file_path)
            else:
                logger.info("Missing model: %s", model_name)
        cls._loaded = True

    @classmethod
    def load(cls, name: str, model_dir: pathlib.Path) -> RemoteModel:
        # To keep compatibility with the old models, we temporarily use the
        # model name as a heuristic to determine the backend
        # Tensorflow Object Detection models are going to be phased out in
        # favor of YOLO models
        backend = "yolo" if "yolo" in name else "tf"
        label_names = list(text_file_iter(model_dir / LABEL_NAMES_FILENAME))

        if backend == "tf":
            label_names.insert(0, "NULL")

        model = RemoteModel(name, label_names, backend=backend)
        cls.models[name] = model
        return model

    @classmethod
    def get(cls, name: str) -> RemoteModel:
        cls.load_all()
        return cls.models[name]
