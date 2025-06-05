import pytest

from robotoff.models import ImagePrediction
from robotoff.prediction.ingredient_list import (
    IngredientPredictionAggregatedEntity,
    IngredientPredictionOutput,
)
from robotoff.prediction.langid import LanguagePrediction
from robotoff.types import ProductIdentifier, ServerType
from robotoff.workers.tasks.import_image import extract_ingredients_job

from ...models_utils import ImageModelFactory, ImagePredictionFactory, clean_db


@pytest.fixture(autouse=True)
def _set_up_and_tear_down(peewee_db):
    with peewee_db:
        clean_db()
        # Run the test case.
    yield

    with peewee_db:
        clean_db()


def test_extract_ingredients_job(mocker, peewee_db):
    full_text = "Best product ever!\ningredients: water, salt, sugar."
    entities = [
        IngredientPredictionAggregatedEntity(
            start=19,
            end=51,
            raw_end=51,
            score=0.9,
            text="water, salt, sugar.",
            lang=LanguagePrediction(lang="en", confidence=0.9),
            bounding_box=(0, 0, 100, 100),
        )
    ]
    parsed_ingredients = [
        {
            "ciqual_food_code": "18066",
            "id": "en:water",
            "percent_estimate": 66.6666666666667,
            "percent_max": 100,
            "percent_min": 33.3333333333333,
            "text": "water",
            "vegan": "yes",
            "vegetarian": "yes",
        },
        {
            "ciqual_food_code": "11058",
            "id": "en:salt",
            "percent_estimate": 16.6666666666667,
            "percent_max": 50,
            "percent_min": 0,
            "text": "salt",
            "vegan": "yes",
            "vegetarian": "yes",
        },
        {
            "id": "en:sugar",
            "percent_estimate": 16.6666666666667,
            "percent_max": 33.3333333333333,
            "percent_min": 0,
            "text": "sugar",
            "vegan": "yes",
            "vegetarian": "yes",
        },
    ]
    ingredient_list_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.ingredient_list"
    )
    parse_ingredients_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.parse_ingredients",
        return_value=parsed_ingredients,
    )
    ingredient_list_mocker.predict_from_ocr.return_value = IngredientPredictionOutput(
        entities=entities, text=full_text
    )
    ingredient_list_mocker.MODEL_NAME = "ingredient_detection"
    ingredient_list_mocker.MODEL_VERSION = "ingredient-detection-1.1"

    import_insights = mocker.patch(
        "robotoff.workers.tasks.import_image.import_insights"
    )
    barcode = "1234567890123"
    ocr_url = "https://images.openfoodfacts.org/images/products/123/456/789/0123/1.json"

    with peewee_db:
        image = ImageModelFactory(
            barcode=barcode,
            server_type=ServerType.off,
            image_id="1",
            width=400,
            height=400,
        )
        extract_ingredients_job(
            ProductIdentifier(barcode, ServerType.off), ocr_url=ocr_url
        )
        ingredient_list_mocker.predict_from_ocr.assert_called_once_with(
            ocr_url, triton_uri=None
        )
        parse_ingredients_mocker.assert_called_once_with("water, salt, sugar.", "en")
        image_prediction = ImagePrediction.get_or_none(
            ImagePrediction.model_name == "ingredient_detection",
            ImagePrediction.image_id == image.id,
        )
        assert image_prediction is not None
        entity = {
            "end": 51,
            "lang": {"lang": "en", "confidence": 0.9},
            "text": "water, salt, sugar.",
            "score": 0.9,
            "start": 19,
            "raw_end": 51,
            "ingredients_n": 3,
            "known_ingredients_n": 3,
            "unknown_ingredients_n": 0,
            "fraction_known_ingredients": 1.0,
            "ingredients": [
                {"in_taxonomy": True, **ingredient} for ingredient in parsed_ingredients
            ],
            "bounding_box": [0.0, 0.0, 0.25, 0.25],
        }
        assert image_prediction.data == {
            "entities": [entity],
        }
        assert image_prediction.max_confidence == 0.9
        assert image_prediction.type == "ner"
        assert image_prediction.model_name == "ingredient_detection"
        assert image_prediction.model_version == "ingredient-detection-1.1"

        assert import_insights.call_count == 1
        assert len(import_insights.call_args.args) == 1
        predictions = import_insights.call_args.args[0]
        assert len(predictions) == 1
        prediction = predictions[0]
        assert prediction.type == "ingredient_detection"
        assert prediction.data == entity
        assert prediction.barcode == barcode
        assert prediction.server_type == ServerType.off
        assert prediction.confidence == 1.0
        assert prediction.value_tag == "en"
        assert prediction.value is None
        assert prediction.automatic_processing is False
        assert prediction.predictor == "ingredient_detection"
        assert prediction.predictor_version == "ingredient-detection-1.1"
        assert prediction.source_image == image.source_image

        assert import_insights.call_args.kwargs == {
            "server_type": ServerType.off,
        }


def test_extract_ingredients_job_missing_image(mocker, peewee_db):
    ingredient_list_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.ingredient_list"
    )
    parse_ingredients_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.parse_ingredients"
    )
    barcode = "1234567890123"
    ocr_url = "https://images.openfoodfacts.org/images/products/123/456/789/0123/1.json"

    with peewee_db:
        extract_ingredients_job(
            ProductIdentifier(barcode, ServerType.off), ocr_url=ocr_url
        )
        ingredient_list_mocker.predict_from_ocr.assert_not_called()
        parse_ingredients_mocker.assert_not_called()


def test_extract_ingredients_job_existing_image_prediction(mocker, peewee_db):
    ingredient_list_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.ingredient_list"
    )
    parse_ingredients_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.parse_ingredients"
    )
    ingredient_list_mocker.MODEL_NAME = "ingredient_detection"
    ingredient_list_mocker.MODEL_VERSION = "ingredient-detection-1.1"

    import_insights = mocker.patch(
        "robotoff.workers.tasks.import_image.import_insights"
    )

    barcode = "1234567890123"
    ocr_url = "https://images.openfoodfacts.org/images/products/123/456/789/0123/1.json"

    with peewee_db:
        image = ImageModelFactory(
            barcode=barcode,
            server_type=ServerType.off,
            image_id="1",
            width=100,
            height=100,
        )
        entity = {
            "end": 51,
            "lang": {"lang": "en", "confidence": 0.9},
            "text": "water, salt, sugar.",
            "score": 0.9,
            "start": 19,
            "raw_end": 51,
            "ingredients_n": 3,
            "known_ingredients_n": 3,
            "unknown_ingredients_n": 0,
            "ingredients": [
                {
                    "id": "en:water",
                    "text": "water",
                    "percent_estimate": 66.6666666666667,
                    "percent_max": 100,
                    "percent_min": 33.3333333333333,
                }
            ],
            "bounding_box": [0, 0, 80, 80],
        }
        ImagePredictionFactory(
            image=image,
            model_name="ingredient_detection",
            model_version="ingredient-detection-1.1",
            data={"entities": [entity]},
            max_confidence=0.9,
            type="ner",
        )
        extract_ingredients_job(
            ProductIdentifier(barcode, ServerType.off), ocr_url=ocr_url
        )
        ingredient_list_mocker.predict_from_ocr.assert_not_called()
        parse_ingredients_mocker.assert_not_called()

        image_prediction = ImagePrediction.get_or_none(
            ImagePrediction.model_name == "ingredient_detection",
            ImagePrediction.image_id == image.id,
        )
        assert image_prediction is not None
        assert len(image_prediction.data["entities"]) == 1
        entity = image_prediction.data["entities"][0]
        assert entity["ingredients_n"] == 3
        assert entity["known_ingredients_n"] == 3
        assert entity["unknown_ingredients_n"] == 0
        # We check that the data is converted to the new schema
        assert entity["fraction_known_ingredients"] == 1.0
        # We check that the bounding box is converted to relative coordinates
        assert entity["bounding_box"] == [0, 0, 0.8, 0.8]

        assert import_insights.call_count == 1
        assert len(import_insights.call_args.args) == 1
        predictions = import_insights.call_args.args[0]
        assert len(predictions) == 1
        prediction = predictions[0]
        assert prediction.type == "ingredient_detection"
        assert prediction.data == entity
        assert prediction.barcode == barcode
        assert prediction.server_type == ServerType.off

        assert import_insights.call_args.kwargs == {
            "server_type": ServerType.off,
        }


def test_extract_ingredients_job_product_opener_api_failed(mocker, peewee_db):
    full_text = "Best product ever!\ningredients: water, salt, sugar."
    entities = [
        IngredientPredictionAggregatedEntity(
            start=19,
            end=51,
            raw_end=51,
            score=0.9,
            text="water, salt, sugar.",
            lang=LanguagePrediction(lang="en", confidence=0.9),
            bounding_box=(0, 0, 100, 100),
        )
    ]
    ingredient_list_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.ingredient_list"
    )

    # make parse_ingredients raise a RuntimeError
    parse_ingredients_mocker = mocker.patch(
        "robotoff.workers.tasks.import_image.parse_ingredients",
        side_effect=RuntimeError("Failed to parse ingredients"),
    )
    ingredient_list_mocker.predict_from_ocr.return_value = IngredientPredictionOutput(
        entities=entities, text=full_text
    )
    ingredient_list_mocker.MODEL_NAME = "ingredient_detection"
    ingredient_list_mocker.MODEL_VERSION = "ingredient-detection-1.1"

    import_insights = mocker.patch(
        "robotoff.workers.tasks.import_image.import_insights"
    )
    barcode = "1234567890123"
    ocr_url = "https://images.openfoodfacts.org/images/products/123/456/789/0123/1.json"

    with peewee_db:
        image = ImageModelFactory(
            barcode=barcode,
            server_type=ServerType.off,
            image_id="1",
            width=400,
            height=400,
        )
        extract_ingredients_job(
            ProductIdentifier(barcode, ServerType.off), ocr_url=ocr_url
        )
        ingredient_list_mocker.predict_from_ocr.assert_called_once_with(
            ocr_url, triton_uri=None
        )
        parse_ingredients_mocker.assert_called_once_with("water, salt, sugar.", "en")
        image_prediction = ImagePrediction.get_or_none(
            ImagePrediction.model_name == "ingredient_detection",
            ImagePrediction.image_id == image.id,
        )
        assert image_prediction is not None
        entity = {
            "end": 51,
            "lang": {"lang": "en", "confidence": 0.9},
            "text": "water, salt, sugar.",
            "score": 0.9,
            "start": 19,
            "raw_end": 51,
            "bounding_box": [0.0, 0.0, 0.25, 0.25],
        }
        assert image_prediction.data == {
            "entities": [entity],
        }
        assert image_prediction.max_confidence == 0.9
        assert image_prediction.type == "ner"
        assert image_prediction.model_name == "ingredient_detection"
        assert image_prediction.model_version == "ingredient-detection-1.1"

        assert import_insights.call_count == 1
        assert len(import_insights.call_args.args) == 1
        predictions = import_insights.call_args.args[0]
        assert len(predictions) == 0
        assert import_insights.call_args.kwargs == {
            "server_type": ServerType.off,
        }
