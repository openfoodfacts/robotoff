import numpy as np
import pytest
from PIL import Image

from robotoff.insights.extraction import extract_nutriscore_label
from robotoff.prediction.object_detection.core import (
    ObjectDetectionRawResult,
    RemoteModel,
)
from robotoff.prediction.types import Prediction, PredictionType


class FakeNutriscoreModel(RemoteModel):
    def __init__(self, raw_result: ObjectDetectionRawResult):
        self.raw_result = raw_result

    def detect_from_image(
        self, image: np.ndarray, output_image: bool = False
    ) -> ObjectDetectionRawResult:
        return self.raw_result


@pytest.mark.parametrize(
    "automatic_threshold, processed_automatically, source_image",
    [
        (None, False, "/image/1"),
        (0.7, True, "/image/1"),
    ],
)
def test_extract_nutriscore_label_automatic(
    mocker, source_image, automatic_threshold, processed_automatically
):
    raw_result = ObjectDetectionRawResult(
        num_detections=1,
        detection_boxes=np.array([[1, 2, 3, 4]]),
        detection_scores=np.array([0.8]),
        detection_classes=np.array([1]),
        category_index={1: {"id": 1, "name": "nutriscore-a"}},
    )
    mocker.patch(
        "robotoff.prediction.object_detection.core.ObjectDetectionModelRegistry.get",
        return_value=FakeNutriscoreModel(raw_result),
    )

    insight = extract_nutriscore_label(
        Image.Image,
        source_image=source_image,
        manual_threshold=0.5,
        automatic_threshold=automatic_threshold,
    )

    assert insight == Prediction(
        type=PredictionType.label,
        data={
            "confidence": 0.8,
            "bounding_box": (1, 2, 3, 4),
            "model": "nutriscore",
            "notify": True,
        },
        source_image=source_image,
        value_tag="en:nutriscore-grade-a",
        automatic_processing=processed_automatically,
    )
