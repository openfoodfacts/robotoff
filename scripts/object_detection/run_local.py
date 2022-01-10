import pathlib

import numpy as np
import PIL
import tensorflow as tf
from PIL import Image

from robotoff.ml.object_detection.core import (
    ObjectDetectionRawResult,
    add_boxes_and_labels,
    convert_image_to_array,
)
from robotoff.ml.object_detection.utils import label_map_util
from robotoff.ml.object_detection.utils.label_map_util import CategoryIndex
from robotoff.utils import get_logger

import utils_ops

logger = get_logger(__name__)


class ObjectDetectionModel:
    def __init__(self, graph: tf.Graph, label_map):
        self.graph: tf.Graph = graph
        self.label_map = label_map

        self.categories = label_map_util.convert_label_map_to_categories(
            label_map, max_num_classes=1000
        )
        self.category_index: CategoryIndex = label_map_util.create_category_index(
            self.categories
        )

    @classmethod
    def load(cls, graph_path: pathlib.Path, label_path: pathlib.Path):
        detection_graph = tf.Graph()
        with detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(str(graph_path), "rb") as f:
                serialized_graph = f.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name="")

        label_map = label_map_util.load_labelmap(str(label_path))

        logger.info("Model loaded")
        return cls(graph=detection_graph, label_map=label_map)

    def _run_inference_for_single_image(
        self, image: np.ndarray
    ) -> ObjectDetectionRawResult:
        with tf.Session(graph=self.graph) as sess:
            # Get handles to input and output tensors
            ops = self.graph.get_operations()
            all_tensor_names = {output.name for op in ops for output in op.outputs}
            tensor_dict = {}
            for key in [
                "num_detections",
                "detection_boxes",
                "detection_scores",
                "detection_classes",
                "detection_masks",
            ]:
                tensor_name = key + ":0"
                if tensor_name in all_tensor_names:
                    tensor_dict[key] = self.graph.get_tensor_by_name(tensor_name)
            if "detection_masks" in tensor_dict:
                # The following processing is only for single image
                detection_boxes = tf.squeeze(tensor_dict["detection_boxes"], [0])
                detection_masks = tf.squeeze(tensor_dict["detection_masks"], [0])
                # Reframe is required to translate mask from box coordinates
                # to image coordinates and fit the image size.
                real_num_detection = tf.cast(tensor_dict["num_detections"][0], tf.int32)
                detection_boxes = tf.slice(
                    detection_boxes, [0, 0], [real_num_detection, -1]
                )
                detection_masks = tf.slice(
                    detection_masks, [0, 0, 0], [real_num_detection, -1, -1]
                )
                detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
                    detection_masks, detection_boxes, image.shape[0], image.shape[1]
                )
                detection_masks_reframed = tf.cast(
                    tf.greater(detection_masks_reframed, 0.5), tf.uint8
                )
                # Follow the convention by adding back the batch dimension
                tensor_dict["detection_masks"] = tf.expand_dims(
                    detection_masks_reframed, 0
                )
            image_tensor = self.graph.get_tensor_by_name("image_tensor:0")

            # Run inference
            output_dict = sess.run(
                tensor_dict, feed_dict={image_tensor: np.expand_dims(image, 0)}
            )

            # all outputs are float32 numpy arrays, so convert types as
            # appropriate
            output_dict["num_detections"] = int(output_dict["num_detections"][0])
            output_dict["detection_classes"] = output_dict["detection_classes"][
                0
            ].astype(np.uint8)
            output_dict["detection_boxes"] = output_dict["detection_boxes"][0]
            output_dict["detection_scores"] = output_dict["detection_scores"][0]
            if "detection_masks" in output_dict:
                output_dict["detection_masks"] = output_dict["detection_masks"][0]

        return ObjectDetectionRawResult(
            num_detections=output_dict["num_detections"],
            detection_classes=output_dict["detection_classes"],
            detection_boxes=output_dict["detection_boxes"],
            detection_scores=output_dict["detection_scores"],
            detection_masks=output_dict.get("detection_masks"),
            category_index=self.category_index,
        )

    def detect_from_image(
        self, image: PIL.Image.Image, output_image: bool = False
    ) -> ObjectDetectionRawResult:
        image_array = convert_image_to_array(image)
        result = self._run_inference_for_single_image(image_array)

        if output_image:
            add_boxes_and_labels(image_array, result)

        return result


def run_model(image_dir: pathlib.Path, model: ObjectDetectionModel):
    for filepath in image_dir.glob("*.jpg"):
        boxed_filename = filepath.parent / "{}_box.jpg".format(filepath.stem)

        if filepath.stem.endswith("box") or boxed_filename.exists():
            continue

        image: PIL.Image.Image = Image.open(str(filepath))
        result = model.detect_from_image(image, output_image=True)

        with open(str(boxed_filename), "wb") as f:
            if result.boxed_image:
                result.boxed_image.save(f)
