import pytest

from robotoff.prediction.utils import (
    get_image_lang,
    get_image_rotation,
    get_nutrition_table_prediction,
)
from robotoff.types import ObjectDetectionModel, PredictionType
from tests.integration.models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    PredictionFactory,
    clean_db,
)


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        # clean db
        clean_db()
        # Run the test case.
        yield
        clean_db()


class TestGetImageRotation:
    def test_get_image_rotation(self, peewee_db):
        with peewee_db:
            prediction = PredictionFactory(
                type=PredictionType.image_orientation, data={"rotation": 90}
            )
            source_image = prediction.source_image
            # Create other prediction
            PredictionFactory(type=PredictionType.image_lang, source_image=source_image)
            result = get_image_rotation(source_image)
            assert result == prediction.data["rotation"]

    def test_get_no_result(self, peewee_db):
        source_image = "/872/032/603/7888/1.jpg"
        with peewee_db:
            PredictionFactory(type=PredictionType.image_lang, source_image=source_image)
            result = get_image_rotation(source_image)
            assert result is None


class TestGetImageLang:
    def test_get_image_lang(self, peewee_db):
        lang_data = {
            "count": {"en": 20, "fil": 7, "null": 12, "words": 39},
            "percent": {
                "en": 51.282051282051285,
                "fil": 17.94871794871795,
                "null": 30.76923076923077,
            },
        }
        with peewee_db:
            prediction = PredictionFactory(
                type=PredictionType.image_lang, data=lang_data
            )
            source_image = prediction.source_image
            # Create other prediction
            PredictionFactory(
                type=PredictionType.image_orientation, source_image=source_image
            )
            result = get_image_lang(source_image)
            assert result == lang_data

    def test_get_no_result(self, peewee_db):
        source_image = "/872/032/603/7888/2.jpg"
        with peewee_db:
            PredictionFactory(
                type=PredictionType.image_orientation, source_image=source_image
            )
            result = get_image_lang(source_image)
            assert result is None


class TestGetNutritionTablePrediction:
    def test_get_nutrition_table_prediction(self, peewee_db):
        detection_data = {
            "objects": [
                {
                    "label": "nutrition-table",
                    "score": 0.9000762104988098,
                    "bounding_box": [
                        0.06199073791503906,
                        0.20298996567726135,
                        0.4177824556827545,
                        0.9909706115722656,
                    ],
                },
                {
                    "label": "nutrition-table",
                    "score": 0.53344119787216187,
                    "bounding_box": [
                        0.3770750164985657,
                        0.0008307297830469906,
                        0.5850498080253601,
                        0.15185657143592834,
                    ],
                },
            ]
        }
        with peewee_db:
            image_model = ImageModelFactory(source_image="/872/032/603/7888/3.jpg")
            ImagePredictionFactory(
                model_name=ObjectDetectionModel.nutrition_table.name,
                data=detection_data,
                image=image_model,
            )
            source_image = image_model.source_image
            result = get_nutrition_table_prediction(source_image)
            assert result == detection_data["objects"]

    def test_get_no_result(self, peewee_db):
        source_image = "/872/032/603/7888/4.jpg"
        with peewee_db:
            ImageModelFactory(source_image=source_image)
            result = get_nutrition_table_prediction(source_image)
            assert result is None

    def test_get_below_threshold(self, peewee_db):
        detection_data = {
            "objects": [
                {
                    "label": "nutrition-table",
                    "score": 0.9000762104988098,
                    "bounding_box": [
                        0.06199073791503906,
                        0.20298996567726135,
                        0.4177824556827545,
                        0.9909706115722656,
                    ],
                },
                {
                    "label": "nutrition-table",
                    "score": 0.53344119787216187,
                    "bounding_box": [
                        0.3770750164985657,
                        0.0008307297830469906,
                        0.5850498080253601,
                        0.15185657143592834,
                    ],
                },
            ]
        }
        with peewee_db:
            image_model = ImageModelFactory(source_image="/872/032/603/7888/5.jpg")
            ImagePredictionFactory(
                model_name=ObjectDetectionModel.nutrition_table.name,
                data=detection_data,
                image=image_model,
            )
            source_image = image_model.source_image
            result = get_nutrition_table_prediction(source_image, threshold=0.95)
            assert result == []
