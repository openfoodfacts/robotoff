import pathlib
from typing import Optional, List, Tuple, Dict

import dataclasses

import PIL

import numpy as np
import tensorflow as tf

from PIL import Image
import requests

from robotoff import settings

from robotoff.ml.object_detection.utils import ops as utils_ops
from robotoff.ml.object_detection.utils.label_map_util import CategoryIndex
from robotoff.ml.object_detection.utils.ops import convert_image_to_array
from robotoff.ml.object_detection.utils.string_int_label_map_pb2 import \
    StringIntLabelMap
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


class ObjectDetectionModel:
    def __init__(self,
                 graph: tf.Graph,
                 label_map: StringIntLabelMap):
        self.graph: tf.Graph = graph
        self.label_map: StringIntLabelMap = label_map

        self.categories = label_map_util.convert_label_map_to_categories(
            label_map, max_num_classes=1000)
        self.category_index: CategoryIndex = (
            label_map_util.create_category_index(self.categories))

    @classmethod
    def load(cls, graph_path: pathlib.Path, label_path: pathlib.Path):
        detection_graph = tf.Graph()
        with detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(
                    str(graph_path), 'rb') as f:
                serialized_graph = f.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

        label_map = label_map_util.load_labelmap(
            str(label_path))

        logger.info("Model loaded")
        return cls(graph=detection_graph,
                   label_map=label_map)

    def _run_inference_for_single_image(self, image: np.array) -> \
            ObjectDetectionRawResult:
        with tf.Session(graph=self.graph) as sess:
            # Get handles to input and output tensors
            ops = self.graph.get_operations()
            all_tensor_names = {output.name for op in ops for output in
                                op.outputs}
            tensor_dict = {}
            for key in [
                'num_detections', 'detection_boxes', 'detection_scores',
                'detection_classes', 'detection_masks'
            ]:
                tensor_name = key + ':0'
                if tensor_name in all_tensor_names:
                    tensor_dict[
                        key] = self.graph.get_tensor_by_name(tensor_name)
            if 'detection_masks' in tensor_dict:
                # The following processing is only for single image
                detection_boxes = tf.squeeze(tensor_dict['detection_boxes'],
                                             [0])
                detection_masks = tf.squeeze(tensor_dict['detection_masks'],
                                             [0])
                # Reframe is required to translate mask from box coordinates
                # to image coordinates and fit the image size.
                real_num_detection = tf.cast(
                    tensor_dict['num_detections'][0],
                    tf.int32)
                detection_boxes = tf.slice(detection_boxes, [0, 0],
                                           [real_num_detection, -1])
                detection_masks = tf.slice(detection_masks, [0, 0, 0],
                                           [real_num_detection, -1, -1])
                detection_masks_reframed = utils_ops. \
                    reframe_box_masks_to_image_masks(
                    detection_masks, detection_boxes, image.shape[0],
                    image.shape[1])
                detection_masks_reframed = tf.cast(
                    tf.greater(detection_masks_reframed, 0.5), tf.uint8)
                # Follow the convention by adding back the batch dimension
                tensor_dict['detection_masks'] = tf.expand_dims(
                    detection_masks_reframed, 0)
            image_tensor = self.graph.get_tensor_by_name('image_tensor:0')

            # Run inference
            output_dict = sess.run(tensor_dict,
                                   feed_dict={
                                       image_tensor: np.expand_dims(image,
                                                                    0)})

            # all outputs are float32 numpy arrays, so convert types as
            # appropriate
            output_dict['num_detections'] = int(
                output_dict['num_detections'][0])
            output_dict['detection_classes'] = output_dict[
                'detection_classes'][0].astype(np.uint8)
            output_dict['detection_boxes'] = output_dict['detection_boxes'][
                0]
            output_dict['detection_scores'] = \
                output_dict['detection_scores'][0]
            if 'detection_masks' in output_dict:
                output_dict['detection_masks'] = \
                    output_dict['detection_masks'][
                        0]

        return ObjectDetectionRawResult(
            image_size=(image.shape[0], image.shape[1]),
            num_detections=output_dict['num_detections'],
            detection_classes=output_dict['detection_classes'],
            detection_boxes=output_dict['detection_boxes'],
            detection_scores=output_dict['detection_scores'],
            detection_masks=output_dict.get('detection_masks'),
            category_index=self.category_index)

    def detect_from_image(self,
                          image: PIL.Image.Image,
                          output_image: bool = False) -> ObjectDetectionRawResult:
        image_array = convert_image_to_array(image)
        result = self._run_inference_for_single_image(image_array)

        if output_image:
            add_boxes_and_labels(image_array, result)

        return result


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
        image_array = np.expand_dims(image_array, 0)
        data = {
            "signature_name": "serving_default",
            "instances": image_array.tolist()
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


def run_model(image_dir: pathlib.Path,
              model: ObjectDetectionModel):
    for filepath in image_dir.glob('*.jpg'):
        boxed_filename = filepath.parent / "{}_box.jpg".format(filepath.stem)

        if filepath.stem.endswith('box') or boxed_filename.exists():
            continue

        image: PIL.Image.Image = Image.open(str(filepath))
        result = model.detect_from_image(image, output_image=True)

        with open(str(boxed_filename), 'wb') as f:
            result.boxed_image.save(f)


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
