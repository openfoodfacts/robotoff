import dataclasses
from unittest.mock import patch

import pytest

from robotoff.models import ImagePrediction
from robotoff.prediction.ingredient_list import (
    IngredientPredictionAggregatedEntity,
    IngredientPredictionOutput,
)
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


@patch("robotoff.workers.tasks.import_image.ingredient_list")
def test_extract_ingredients_job(mocker, peewee_db):
    full_text = "Best product ever!\ningredients: water, salt, sugar."
    entities = [
        IngredientPredictionAggregatedEntity(
            start=19, end=51, score=0.9, text="water, salt, sugar."
        )
    ]
    mocker.predict_from_ocr.return_value = IngredientPredictionOutput(
        entities=entities, text=full_text
    )
    mocker.MODEL_NAME = "ingredient-detection"
    mocker.MODEL_VERSION = "ingredient-detection-1.0"

    barcode = "1234567890123"
    ocr_url = "https://images.openfoodfacts.org/images/products/123/456/789/0123/1.json"

    with peewee_db:
        image = ImageModelFactory(
            barcode=barcode, server_type=ServerType.off, image_id="1"
        )
        extract_ingredients_job(
            ProductIdentifier(barcode, ServerType.off), ocr_url=ocr_url
        )
        mocker.predict_from_ocr.assert_called_once_with(ocr_url)
        image_prediction = ImagePrediction.get_or_none(
            ImagePrediction.model_name == "ingredient-detection",
            ImagePrediction.image_id == image.id,
        )
        assert image_prediction is not None
        assert image_prediction.data == {
            "text": full_text,
            "entities": [dataclasses.asdict(entities[0])],
        }
        assert image_prediction.max_confidence == 0.9
        assert image_prediction.type == "ner"
        assert image_prediction.model_name == "ingredient-detection"
        assert image_prediction.model_version == "ingredient-detection-1.0"


@patch("robotoff.workers.tasks.import_image.ingredient_list")
def test_extract_ingredients_job_missing_image(mocker, peewee_db):
    barcode = "1234567890123"
    ocr_url = "https://images.openfoodfacts.org/images/products/123/456/789/0123/1.json"

    with peewee_db:
        extract_ingredients_job(
            ProductIdentifier(barcode, ServerType.off), ocr_url=ocr_url
        )
        mocker.predict_from_ocr.assert_not_called()


@patch("robotoff.workers.tasks.import_image.ingredient_list")
def test_extract_ingredients_job_existing_image_prediction(mocker, peewee_db):
    mocker.MODEL_NAME = "ingredient-detection"
    mocker.MODEL_VERSION = "ingredient-detection-1.0"
    barcode = "1234567890123"
    ocr_url = "https://images.openfoodfacts.org/images/products/123/456/789/0123/1.json"

    with peewee_db:
        image = ImageModelFactory(
            barcode=barcode, server_type=ServerType.off, image_id="1"
        )
        ImagePredictionFactory(
            image=image,
            model_name="ingredient-detection",
            model_version="ingredient-detection-1.0",
        )
        extract_ingredients_job(
            ProductIdentifier(barcode, ServerType.off), ocr_url=ocr_url
        )
        mocker.predict_from_ocr.assert_not_called()
