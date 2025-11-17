import numpy as np
import pytest
from PIL import Image

from robotoff.insights.extraction import run_object_detection_model
from robotoff.models import ImagePrediction
from robotoff.prediction.object_detection.core import ObjectDetectionResult, RemoteModel
from robotoff.types import ObjectDetectionModel

from ..models_utils import ImageModelFactory, clean_db


@pytest.fixture()
def image_model(peewee_db):
    with peewee_db:
        clean_db()
        yield ImageModelFactory(source_image="/1/1.jpg")
        clean_db()


class FakeNutriscoreModel(RemoteModel):
    def __init__(self, raw_result: ObjectDetectionResult):
        self.raw_result = raw_result

    def detect_from_image(
        self,
        image: Image.Image | np.ndarray,
        output_image: bool = False,
        triton_uri: str | None = None,
        threshold: float | None = 0.5,
        nms_threshold: float | None = None,
        nms_eta: float | None = None,
    ) -> ObjectDetectionResult:
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
    result = ObjectDetectionResult(
        num_detections=1,
        detection_boxes=np.array([[1, 2, 3, 4]]),
        detection_scores=np.array([0.8]),
        detection_classes=np.array([1]),
        label_names=label_names,
    )
    mocker.patch(
        "robotoff.prediction.object_detection.core.ObjectDetectionModelRegistry.get",
        return_value=FakeNutriscoreModel(result),
    )
    image_prediction = run_object_detection_model(
        model_name=model_name,
        image=None,
        image_model=image_model,
        threshold=0.1,
    )
    assert isinstance(image_prediction, ImagePrediction)
    assert image_prediction.type == "object_detection"
    assert image_prediction.model_name == model_name.name
    assert image_prediction.data == {
        "objects": [
            {"bounding_box": (1, 2, 3, 4), "score": 0.8, "label": label_names[1]}
        ]
    }
    assert image_prediction.max_confidence == 0.8
