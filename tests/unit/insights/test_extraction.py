from typing import Optional

import numpy as np
from PIL import Image
import pytest

from robotoff.insights.extraction import (
    extract_nutriscore_label,
    get_barcode_from_url,
    get_source_from_ocr_url,
)
from robotoff.prediction.object_detection.core import (
    ObjectDetectionRawResult,
    RemoteModel,
)
from robotoff.prediction.types import Prediction, PredictionType


@pytest.mark.parametrize(
    "url,output",
    [
        ("/541/012/672/6954/1.jpg", "5410126726954"),
        ("/541/012/672/6954/1.json", "5410126726954"),
        ("/invalid/1.json", None),
        ("/252/535.bk/1.jpg", None),
    ],
)
def test_get_barcode_from_url(url: str, output: Optional[str]):
    assert get_barcode_from_url(url) == output


@pytest.mark.parametrize(
    "url,output",
    [
        (
            "https://static.openfoodfacts.org/images/products/359/671/046/5248/3.jpg",
            "/359/671/046/5248/3.jpg",
        ),
        (
            "https://static.openfoodfacts.org/images/products/2520549/1.jpg",
            "/2520549/1.jpg",
        ),
    ],
)
def test_get_source_from_ocr_url(url: str, output: str):
    assert get_source_from_ocr_url(url) == output


class FakeNutriscoreModel(RemoteModel):
    def __init__(self, raw_result: ObjectDetectionRawResult):
        self.raw_result = raw_result

    def detect_from_image(
        self, image: np.ndarray, output_image: bool = False
    ) -> ObjectDetectionRawResult:
        return self.raw_result


@pytest.mark.parametrize(
    "automatic_threshold, processed_automatically", [(None, False,), (0.7, True,)],
)
def test_extract_nutriscore_label_automatic(
    mocker, automatic_threshold, processed_automatically
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
        Image.Image, manual_threshold=0.5, automatic_threshold=automatic_threshold
    )

    assert insight == Prediction(
        type=PredictionType.label,
        data={
            "confidence": 0.8,
            "bounding_box": (1, 2, 3, 4),
            "model": "nutriscore",
            "notify": True,
        },
        value_tag="en:nutriscore-grade-a",
        automatic_processing=processed_automatically,
    )
