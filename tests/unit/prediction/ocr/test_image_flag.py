import pytest
import requests
from openfoodfacts.ocr import OCRResult

from robotoff.prediction.ocr.image_flag import flag_image
from robotoff.types import PredictionType


@pytest.fixture
def face_detection_ocr_result():
    test_data_url = "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/unit/ocr/face_detection.json"
    response = requests.get(test_data_url)
    response.raise_for_status()
    return OCRResult.from_json(response.json())


def test_flag_image_with_face_annotation(face_detection_ocr_result):
    predictions = flag_image(face_detection_ocr_result)

    assert predictions

    face_predictions = [
        pred
        for pred in predictions
        if pred.type == PredictionType.image_flag
        and pred.data.get("type") == "face_annotation"
    ]

    assert face_predictions
    assert len(face_predictions) == 1

    face_prediction = face_predictions[0]
    assert face_prediction.data["label"] == "face"
    assert face_prediction.data["type"] == "face_annotation"
    assert face_prediction.data["likelihood"] == 0.92
    assert face_prediction.confidence == 0.92


def test_flag_image_with_label_annotation_face():
    ocr_json = {
        "responses": [{"labelAnnotations": [{"description": "Face", "score": 0.8}]}]
    }

    ocr_result = OCRResult.from_json(ocr_json)
    predictions = flag_image(ocr_result)

    face_predictions = [
        pred
        for pred in predictions
        if pred.type == PredictionType.image_flag
        and pred.data.get("type") == "label_annotation"
        and pred.data.get("label") == "face"
    ]

    assert face_predictions, "No face label predictions were detected"
    assert len(face_predictions) == 1, "Expected exactly one face label prediction"
    assert face_predictions[0].data["likelihood"] == 0.8


def test_flag_image_with_safe_search():
    ocr_json = {
        "responses": [
            {
                "safeSearchAnnotation": {
                    "adult": "VERY_LIKELY",
                    "spoof": "VERY_UNLIKELY",
                    "medical": "UNLIKELY",
                    "violence": "VERY_UNLIKELY",
                    "racy": "VERY_UNLIKELY",
                }
            }
        ]
    }

    ocr_result = OCRResult.from_json(ocr_json)
    predictions = flag_image(ocr_result)

    safe_search_predictions = [
        pred
        for pred in predictions
        if pred.type == PredictionType.image_flag
        and pred.data.get("type") == "safe_search_annotation"
        and pred.data.get("label") == "adult"
    ]

    assert safe_search_predictions, "No safe search predictions were detected"
    assert (
        len(safe_search_predictions) == 1
    ), "Expected exactly one safe search prediction"
    assert safe_search_predictions[0].data["likelihood"] == "VERY_LIKELY"


def test_flag_image_below_threshold():
    ocr_json = {
        "responses": [
            {
                "faceAnnotations": [
                    {
                        "detectionConfidence": 0.4,  # Below 0.6 threshold
                        "joyLikelihood": "VERY_LIKELY",
                        "sorrowLikelihood": "VERY_UNLIKELY",
                        "angerLikelihood": "VERY_UNLIKELY",
                        "surpriseLikelihood": "UNLIKELY",
                    }
                ]
            }
        ]
    }

    ocr_result = OCRResult.from_json(ocr_json)
    predictions = flag_image(ocr_result)

    face_predictions = [
        pred
        for pred in predictions
        if pred.type == PredictionType.image_flag
        and pred.data.get("type") == "face_annotation"
    ]

    assert (
        not face_predictions
    ), "Face predictions were created despite being below threshold"


def test_multiple_faces_highest_confidence():
    ocr_json = {
        "responses": [
            {
                "faceAnnotations": [
                    {"detectionConfidence": 0.7, "joyLikelihood": "VERY_LIKELY"},
                    {
                        "detectionConfidence": 0.9,  # This one should be chosen
                        "joyLikelihood": "UNLIKELY",
                    },
                    {"detectionConfidence": 0.8, "joyLikelihood": "POSSIBLE"},
                ]
            }
        ]
    }

    ocr_result = OCRResult.from_json(ocr_json)
    predictions = flag_image(ocr_result)

    face_predictions = [
        pred
        for pred in predictions
        if pred.type == PredictionType.image_flag
        and pred.data.get("type") == "face_annotation"
    ]

    assert face_predictions, "No face predictions were detected"
    assert len(face_predictions) == 1, "Expected exactly one face prediction"
    assert face_predictions[0].data["likelihood"] == 0.9
