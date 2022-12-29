import dataclasses
import pathlib
from typing import Optional

import numpy as np
from PIL import Image
from tritonclient.grpc import service_pb2

from robotoff import settings
from robotoff.prediction.object_detection.utils import visualization_utils as vis_util
from robotoff.triton import get_triton_inference_stub
from robotoff.types import JSONType, ObjectDetectionModel
from robotoff.utils import get_logger, text_file_iter

logger = get_logger(__name__)

LABEL_NAMES_FILENAME = "labels.txt"


OBJECT_DETECTION_MODEL_VERSION = {
    ObjectDetectionModel.nutriscore: "tf-nutriscore-1.0",
    ObjectDetectionModel.nutrition_table: "tf-nutrition-table-1.0",
    ObjectDetectionModel.universal_logo_detector: "tf-universal-logo-detector-1.0",
}


@dataclasses.dataclass
class ObjectDetectionResult:
    bounding_box: tuple
    score: float
    label: str


@dataclasses.dataclass
class ObjectDetectionRawResult:
    num_detections: int
    detection_boxes: np.ndarray
    detection_scores: np.ndarray
    detection_classes: np.ndarray
    label_names: list[str]
    detection_masks: Optional[np.ndarray] = None
    boxed_image: Optional[Image.Image] = None

    def select(self, threshold: Optional[float] = None) -> list[ObjectDetectionResult]:
        if threshold is None:
            threshold = 0.5

        box_masks = self.detection_scores > threshold
        selected_boxes = self.detection_boxes[box_masks]
        selected_scores = self.detection_scores[box_masks]
        selected_classes = self.detection_classes[box_masks]

        results = []
        for bounding_box, score, label in zip(
            selected_boxes, selected_scores, selected_classes
        ):
            label_int = int(label)
            label_str = self.label_names[label_int]
            if label_str is not None:
                result = ObjectDetectionResult(
                    bounding_box=tuple(bounding_box.tolist()),
                    score=float(score),
                    label=label_str,
                )
                results.append(result)

        return results

    def to_json(self, threshold: Optional[float] = None) -> list[JSONType]:
        return [dataclasses.asdict(r) for r in self.select(threshold)]


def convert_image_to_array(image: Image.Image) -> np.ndarray:
    if image.mode != "RGB":
        image = image.convert("RGB")

    (im_width, im_height) = image.size

    return np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)


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
    width, height = image.size
    max_width, max_height = max_size

    if width > max_width or height > max_height:
        new_image = image.copy()
        new_image.thumbnail((max_width, max_height))
        return new_image

    return image


class RemoteModel:
    def __init__(self, name: str, label_names: list[str]):
        self.name: str = name
        self.label_names = label_names

    def detect_from_image(
        self, image: Image.Image, output_image: bool = False
    ) -> ObjectDetectionRawResult:
        resized_image = resize_image(image, settings.OBJECT_DETECTION_IMAGE_MAX_SIZE)
        image_array = convert_image_to_array(resized_image)
        grpc_stub = get_triton_inference_stub()
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
        response = grpc_stub.ModelInfer(request)

        if len(response.outputs) != 4:
            raise Exception(f"expected 4 output, got {len(response.outputs)}")

        if len(response.raw_output_contents) != 4:
            raise Exception(
                f"expected 4 raw output content, got {len(response.raw_output_contents)}"
            )

        output_index = {output.name: i for i, output in enumerate(response.outputs)}
        num_detections = (
            np.frombuffer(
                response.raw_output_contents[output_index["num_detections"]],
                dtype=np.float32,
            )
            .reshape((1, 1))
            .astype(np.int)[0][0]  # type: ignore
        )
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

        result = ObjectDetectionRawResult(
            num_detections=num_detections,
            detection_classes=detection_classes,
            detection_boxes=detection_boxes,
            detection_scores=detection_scores,
            detection_masks=None,
            label_names=self.label_names,
        )

        if output_image:
            add_boxes_and_labels(image_array, result)

        return result


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
            file_path = settings.MODELS_DIR / model_name
            if file_path.is_dir():
                logger.info("Model %s found", model_name)
                cls.models[model_name] = cls.load(model_name, file_path)
            else:
                logger.info("Missing model: %s", model_name)
        cls._loaded = True

    @classmethod
    def load(cls, name: str, model_dir: pathlib.Path) -> RemoteModel:
        label_names = ["NULL"] + list(text_file_iter(model_dir / LABEL_NAMES_FILENAME))
        model = RemoteModel(name, label_names)
        cls.models[name] = model
        return model

    @classmethod
    def get(cls, name: str) -> RemoteModel:
        cls.load_all()
        return cls.models[name]
