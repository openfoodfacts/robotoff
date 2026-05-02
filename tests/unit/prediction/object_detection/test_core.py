from types import SimpleNamespace

import numpy as np
import pytest
from openfoodfacts.ml.object_detection import ObjectDetector

from robotoff.prediction.object_detection.core import OptimizedObjectDetector


def build_response(num_classes: int, rows: int = 512):
    rng = np.random.default_rng(123)
    output = rng.random((1, num_classes + 4, rows), dtype=np.float32)
    output[:, 4:, :] *= 0.4
    output[:, 4:, : min(rows, 64)] += 0.7
    return SimpleNamespace(
        outputs=[SimpleNamespace(name="output0")],
        raw_output_contents=[output.tobytes()],
    )


@pytest.mark.parametrize("num_classes", [1, 5])
@pytest.mark.parametrize("nms", [False, True])
def test_optimized_object_detector_postprocess_matches_upstream(
    num_classes: int, nms: bool
):
    label_names = [f"class_{i}" for i in range(num_classes)]
    response = build_response(num_classes=num_classes)
    original_shape = (3024, 4032)

    upstream_detector = ObjectDetector(
        model_name="test-model",
        label_names=label_names,
        image_size=640,
    )
    optimized_detector = OptimizedObjectDetector(
        model_name="test-model",
        label_names=label_names,
        image_size=640,
    )

    upstream_result = upstream_detector.postprocess(
        response=response,
        threshold=0.5,
        original_shape=original_shape,
        nms=nms,
    )
    optimized_result = optimized_detector.postprocess(
        response=response,
        threshold=0.5,
        original_shape=original_shape,
        nms=nms,
    )

    assert upstream_result.num_detections == optimized_result.num_detections
    assert np.array_equal(
        upstream_result.detection_classes,
        optimized_result.detection_classes,
    )
    assert np.allclose(
        upstream_result.detection_scores,
        optimized_result.detection_scores,
    )
    assert np.allclose(
        upstream_result.detection_boxes,
        optimized_result.detection_boxes,
    )
