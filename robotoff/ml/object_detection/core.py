import pathlib
from typing import Optional, List, Tuple, Dict

import dataclasses

import PIL

import numpy as np

from PIL import Image
import requests

from robotoff import settings

from robotoff.ml.object_detection.utils.label_map_util import CategoryIndex
from robotoff.ml.object_detection.utils import label_map_util
from robotoff.ml.object_detection.utils import visualization_utils as \
    vis_util
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


FROZEN_GRAPH_NAME = 'frozen_inference_graph.pb'
LABEL_MAP_NAME = 'labels.pbtxt'

TF_SERVING_BASE_URL = "http://{}:{}/v1/models".format(
    settings.TF_SERVING_HOST,
    settings.TF_SERVING_HTTP_PORT)

http_session = requests.session()


@dataclasses.dataclass
class ObjectDetectionResult:
    bounding_box: Tuple[float, float, float, float]
    score: float
    label: str


@dataclasses.dataclass
class ObjectDetectionRawResult:
    num_detections: int
    detection_boxes: np.array
    detection_scores: np.array
    detection_classes: np.array
    image_size: Tuple[int, int]
    category_index: CategoryIndex
    detection_masks: Optional[np.array] = None
    boxed_image: Optional[PIL.Image.Image] = None

    def select(self, threshold: Optional[float] = None) -> \
            List[ObjectDetectionResult]:
        if threshold is None:
            threshold = 0.5

        box_masks = (self.detection_scores > threshold)
        selected_boxes = self.detection_boxes[box_masks]
        selected_scores = self.detection_scores[box_masks]
        selected_classes = self.detection_classes[box_masks]

        results = []
        image_width, image_height = self.image_size
        for box, score, label in zip(selected_boxes, selected_scores,
                                     selected_classes):
            ymin, xmin, ymax, xmax = box
            bounding_box = (ymin * image_height, xmin * image_width,
                            ymax * image_height, xmax * image_width)

            label_int = int(label)
            label_str = self.category_index[label_int]['name']
            result = ObjectDetectionResult(bounding_box=bounding_box,
                                           score=float(score),
                                           label=label_str)
            results.append(result)

        return results

    def to_json(self, threshold: Optional[float] = None) -> List[JSONType]:
        return [dataclasses.asdict(r) for r in self.select(threshold)]


def convert_image_to_array(image: PIL.Image.Image) -> np.array:
    if image.mode != 'RGB':
        image = image.convert('RGB')

    (im_width, im_height) = image.size

    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)


def add_boxes_and_labels(image_array: np.array,
                         raw_result: ObjectDetectionRawResult):
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_array,
        raw_result.detection_boxes,
        raw_result.detection_classes,
        raw_result.detection_scores,
        raw_result.category_index,
        instance_masks=raw_result.detection_masks,
        use_normalized_coordinates=True,
        line_thickness=5)
    image_with_boxes = Image.fromarray(image_array)
    raw_result.boxed_image = image_with_boxes


class RemoteModel:
    def __init__(self, name: str, label_path: pathlib.Path):
        self.name: str = name
        label_map = label_map_util.load_labelmap(
            str(label_path))
        self.categories = label_map_util.convert_label_map_to_categories(
            label_map, max_num_classes=1000)
        self.category_index: CategoryIndex = (
            label_map_util.create_category_index(self.categories))

    def detect_from_image(self, image: np.array,
                          output_image: bool = False) -> \
            ObjectDetectionRawResult:
        image_array = convert_image_to_array(image)
        data = {
            "signature_name": "serving_default",
            "instances": np.expand_dims(image_array, 0).tolist()
        }

        r = http_session.post('{}/{}:predict'.format(TF_SERVING_BASE_URL,
                                                     self.name),
                              json=data)
        r.raise_for_status()
        response = r.json()
        prediction = response['predictions'][0]
        num_detections = int(prediction['num_detections'])
        detection_classes = np.array(prediction['detection_classes'],
                                     dtype=np.uint8)
        detection_scores = np.array(prediction['detection_scores'])
        detection_boxes = np.array(prediction['detection_boxes'])

        result = ObjectDetectionRawResult(
            image_size=(image_array.shape[0], image_array.shape[1]),
            num_detections=num_detections,
            detection_classes=detection_classes,
            detection_boxes=detection_boxes,
            detection_scores=detection_scores,
            detection_masks=None,
            category_index=self.category_index)

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
        for filepath in settings.TF_SERVING_MODELS_PATH.glob('*'):
            if filepath.is_dir():
                model_name = filepath.name
                logger.info("TF model '{}' found".format(model_name))
                cls.models[filepath.name] = cls.load(filepath.name, filepath)

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
