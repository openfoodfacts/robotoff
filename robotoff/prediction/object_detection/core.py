import dataclasses
import pathlib
from typing import Dict, List, Optional, Tuple

import numpy as np
import PIL
from PIL import Image

from robotoff import settings
from robotoff.prediction.object_detection.utils import label_map_util
from robotoff.prediction.object_detection.utils import visualization_utils as vis_util
from robotoff.prediction.object_detection.utils.label_map_util import CategoryIndex
from robotoff.utils import get_logger, http_session
from robotoff.utils.types import JSONType

logger = get_logger(__name__)

LABEL_MAP_NAME = "labels.pbtxt"


@dataclasses.dataclass
class ObjectDetectionResult:
    bounding_box: Tuple
    score: float
    label: str


@dataclasses.dataclass
class ObjectDetectionRawResult:
    num_detections: int
    detection_boxes: np.ndarray
    detection_scores: np.ndarray
    detection_classes: np.ndarray
    category_index: CategoryIndex
    detection_masks: Optional[np.ndarray] = None
    boxed_image: Optional[PIL.Image.Image] = None

    def select(self, threshold: Optional[float] = None) -> List[ObjectDetectionResult]:
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
            label_str = self.category_index.get(label_int, {}).get("name")
            if label_str is not None:
                result = ObjectDetectionResult(
                    bounding_box=tuple(bounding_box.tolist()),
                    score=float(score),
                    label=label_str,
                )
                results.append(result)

        return results

    def to_json(self, threshold: Optional[float] = None) -> List[JSONType]:
        return [dataclasses.asdict(r) for r in self.select(threshold)]


def convert_image_to_array(image: PIL.Image.Image) -> np.ndarray:
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
        raw_result.category_index,
        instance_masks=raw_result.detection_masks,
        use_normalized_coordinates=True,
        line_thickness=5,
    )
    image_with_boxes = Image.fromarray(image_array)
    raw_result.boxed_image = image_with_boxes


def resize_image(image: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    width, height = image.size
    max_width, max_height = max_size

    if width > max_width or height > max_height:
        new_image = image.copy()
        new_image.thumbnail((max_width, max_height))
        return new_image

    return image


class RemoteModel:
    def __init__(self, name: str, label_path: pathlib.Path):
        self.name: str = name
        label_map = label_map_util.load_labelmap(str(label_path))
        self.categories = label_map_util.convert_label_map_to_categories(
            label_map, max_num_classes=1000
        )
        self.category_index: CategoryIndex = label_map_util.create_category_index(
            self.categories
        )

    def detect_from_image(
        self, image: np.ndarray, output_image: bool = False
    ) -> ObjectDetectionRawResult:
        resized_image = resize_image(image, settings.OBJECT_DETECTION_IMAGE_MAX_SIZE)
        image_array = convert_image_to_array(resized_image)
        data = {
            "signature_name": "serving_default",
            "instances": np.expand_dims(image_array, 0).tolist(),
        }

        r = http_session.post(
            "{}/{}:predict".format(settings.TF_SERVING_BASE_URL, self.name), json=data
        )
        r.raise_for_status()
        response = r.json()
        prediction = response["predictions"][0]
        num_detections = int(prediction["num_detections"])
        detection_classes = np.array(prediction["detection_classes"], dtype=np.uint8)
        detection_scores = np.array(prediction["detection_scores"])
        detection_boxes = np.array(prediction["detection_boxes"])

        result = ObjectDetectionRawResult(
            num_detections=num_detections,
            detection_classes=detection_classes,
            detection_boxes=detection_boxes,
            detection_scores=detection_scores,
            detection_masks=None,
            category_index=self.category_index,
        )

        if output_image:
            add_boxes_and_labels(image_array, result)

        return result


class ObjectDetectionModelRegistry:
    models: Dict[str, RemoteModel] = {}

    @classmethod
    def get_available_models(cls) -> List[str]:
        return list(cls.models.keys())

    @classmethod
    def load_all(cls):
        for model_name in settings.OBJECT_DETECTION_TF_SERVING_MODELS:
            file_path = settings.TF_SERVING_MODELS_PATH / model_name
            if file_path.is_dir():
                logger.info("TF model '{}' found".format(model_name))
                cls.models[model_name] = cls.load(model_name, file_path)
            else:
                logger.info("Missing TF model: '{}'".format(model_name))

    @classmethod
    def load(cls, name: str, model_dir: pathlib.Path) -> RemoteModel:
        label_path = model_dir / LABEL_MAP_NAME
        model = RemoteModel(name, label_path)
        cls.models[name] = model
        return model

    @classmethod
    def get(cls, name: str) -> RemoteModel:
        return cls.models[name]


ObjectDetectionModelRegistry.load_all()
