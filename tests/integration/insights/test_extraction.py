import numpy as np
import pytest
from PIL import Image

from robotoff.insights.extraction import run_object_detection_model
from robotoff.models import ImagePrediction
from robotoff.prediction.object_detection.core import (
    ObjectDetectionModel,
    ObjectDetectionRawResult,
    RemoteModel,
)

from ..models_utils import ImageModelFactory, clean_db


@pytest.fixture()
def image_model(peewee_db):
    with peewee_db:
        clean_db()
        yield ImageModelFactory(source_image="/1/1.jpg")
        clean_db()


class FakeNutriscoreModel(RemoteModel):
    def __init__(self, raw_result: ObjectDetectionRawResult):
        self.raw_result = raw_result

    def detect_from_image(
        self, image: Image.Image, output_image: bool = False
    ) -> ObjectDetectionRawResult:
        return self.raw_result


@pytest.mark.parametrize(
    "model_name,label_names",
    [
        (ObjectDetectionModel.universal_logo_detector, ["brand", "label"]),
        (
            ObjectDetectionModel.nutriscore,
            [
                "nutriscore-a",
                "nutriscore-b",
                "nutriscore-d",
                "nutriscore-d",
                "nutriscore-e",
            ],
        ),
    ],
)
def test_run_object_detection_model(mocker, image_model, model_name, label_names):
    raw_result = ObjectDetectionRawResult(
        num_detections=1,
        detection_boxes=np.array([[1, 2, 3, 4]]),
        detection_scores=np.array([0.8]),
        detection_classes=np.array([1]),
        label_names=label_names,
    )
    mocker.patch(
        "robotoff.prediction.object_detection.core.ObjectDetectionModelRegistry.get",
        return_value=FakeNutriscoreModel(raw_result),
    )
    image_prediction = run_object_detection_model(
        model_name,
        None,
        source_image=image_model.source_image,
        threshold=0.1,
    )
    assert isinstance(image_prediction, ImagePrediction)
    assert image_prediction.type == "object_detection"
    assert image_prediction.model_name == model_name.value
    assert image_prediction.data == {
        "objects": [
            {"bounding_box": (1, 2, 3, 4), "score": 0.8, "label": label_names[1]}
        ]
    }
    assert image_prediction.max_confidence == 0.8


def test_run_object_detection_model_no_image_instance(peewee_db):
    with peewee_db:
        image_prediction = run_object_detection_model(
            ObjectDetectionModel.nutriscore,
            None,
            source_image="/images/1/1.jpg",
            threshold=0.1,
        )
    assert image_prediction is None
