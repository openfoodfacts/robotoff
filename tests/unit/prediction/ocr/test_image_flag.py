import pytest
from openfoodfacts.ocr import OCRResult

from robotoff.prediction.ocr.image_flag import flag_image
from robotoff.types import Prediction, PredictionType


@pytest.fixture
def face_detection_ocr_result():
    test_data_url = "https://raw.githubusercontent.com/openfoodfacts/test-data/main/robotoff/tests/unit/ocr/face_detection.json"
    return OCRResult.from_url(test_data_url)


def test_flag_image_with_face_annotation(face_detection_ocr_result):
    predictions = flag_image(face_detection_ocr_result)

    face_predictions = [
        pred
        for pred in predictions
        if pred.type == PredictionType.image_flag
        and pred.data.get("type") == "face_annotation"
    ]

    assert face_predictions

    face_prediction = face_predictions[0]
    expected_prediction = Prediction(
        type=PredictionType.image_flag,
        data={"label": "face", "type": "face_annotation", "likelihood": 0.92},
        confidence=0.92,
        predictor_version="1",
    )

    assert face_prediction.type == expected_prediction.type
    assert face_prediction.data == expected_prediction.data
    assert face_prediction.confidence == expected_prediction.confidence


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

    assert face_predictions

    expected_prediction = Prediction(
        type=PredictionType.image_flag,
        data={"label": "face", "type": "label_annotation", "likelihood": 0.8},
        confidence=0.8,
        predictor_version="1",
    )

    assert face_predictions[0].type == expected_prediction.type
    assert face_predictions[0].data == expected_prediction.data
    assert face_predictions[0].confidence == expected_prediction.confidence


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

    assert safe_search_predictions

    expected_prediction = Prediction(
        type=PredictionType.image_flag,
        data={
            "label": "adult",
            "type": "safe_search_annotation",
            "likelihood": "VERY_LIKELY",
        },
        confidence=None,
        predictor_version="1",
    )

    assert safe_search_predictions[0].type == expected_prediction.type
    assert safe_search_predictions[0].data == expected_prediction.data
    assert safe_search_predictions[0].confidence == expected_prediction.confidence


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

    assert not face_predictions


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

    assert face_predictions

    expected_prediction = Prediction(
        type=PredictionType.image_flag,
        data={"label": "face", "type": "face_annotation", "likelihood": 0.9},
        confidence=0.9,
        predictor_version="1",
    )

    assert face_predictions[0].type == expected_prediction.type
    assert face_predictions[0].data == expected_prediction.data
    assert face_predictions[0].confidence == expected_prediction.confidence
