import numpy as np
import pytest

from robotoff.models import ImagePrediction, LogoEmbedding, Prediction, ProductInsight
from robotoff.off import generate_image_url, generate_json_ocr_url
from robotoff.prediction.ingredient_list import (
    IngredientPredictionAggregatedEntity,
    IngredientPredictionOutput,
)
from robotoff.prediction.langid import LanguagePrediction
from robotoff.prediction.nutrition_extraction import (
    NutrientPrediction,
    NutritionEntities,
    NutritionExtractionPrediction,
)
from robotoff.types import (
    InsightImportResult,
    PredictionType,
    ProductIdentifier,
    ServerType,
)
from robotoff.workers.queues import get_high_queue
from robotoff.workers.tasks.import_image import (
    extract_ingredients_job,
    extract_nutrition_job,
)
from robotoff.workers.tasks.import_image import (
    nutrition_extraction as nutrition_extraction_module,
)
from robotoff.workers.tasks.import_image import (
    process_created_logos,
    process_ingredient_prediction_job,
    process_nutrition_prediction_job,
    save_logo_embeddings,
)

from ...models_utils import (
    ImageModelFactory,
    ImagePredictionFactory,
    LogoAnnotationFactory,
    LogoEmbeddingFactory,
    clean_db,
)

DEFAULT_BARCODE = "1234567890123"
DEFAULT_IMAGE_ID = "1"
DEFAULT_SOURCE_IMAGE = "/123/456/789/0123/1.jpg"
DEFAULT_SERVER_TYPE = ServerType.off


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

    enqueue_job = mocker.patch("robotoff.workers.tasks.import_image.enqueue_job")
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

        assert enqueue_job.call_count == 1
        assert len(enqueue_job.call_args.args) == 0
        assert enqueue_job.call_args.kwargs == {
            "func": process_ingredient_prediction_job,
            "queue": get_high_queue(ProductIdentifier(barcode, ServerType.off)),
            "job_kwargs": {"result_ttl": 0},
            "product_id": ProductIdentifier(barcode, ServerType.off),
            "image_prediction_id": image_prediction.id,
            "source_image": image.source_image,
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
    enqueue_job = mocker.patch("robotoff.workers.tasks.import_image.enqueue_job")

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

        assert enqueue_job.call_count == 1
        assert enqueue_job.call_args.args == ()
        assert enqueue_job.call_args.kwargs == {
            "func": process_ingredient_prediction_job,
            "queue": get_high_queue(ProductIdentifier(barcode, ServerType.off)),
            "job_kwargs": {"result_ttl": 0},
            "product_id": ProductIdentifier(barcode, ServerType.off),
            "image_prediction_id": image_prediction.id,
            "source_image": image.source_image,
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

    enqueue_job = mocker.patch("robotoff.workers.tasks.import_image.enqueue_job")
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

        assert enqueue_job.call_count == 1
        assert len(enqueue_job.call_args.args) == 0
        assert enqueue_job.call_args.kwargs == {
            "func": process_ingredient_prediction_job,
            "queue": get_high_queue(ProductIdentifier(barcode, ServerType.off)),
            "job_kwargs": {"result_ttl": 0},
            "product_id": ProductIdentifier(barcode, ServerType.off),
            "image_prediction_id": image_prediction.id,
            "source_image": image.source_image,
        }


def test_process_ingredient_prediction_job(mocker, peewee_db):
    import_insights = mocker.patch(
        "robotoff.workers.tasks.import_image.import_insights"
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
        "fraction_known_ingredients": 1.0,
        "ingredients": [],
        "bounding_box": [0.0, 0.0, 0.25, 0.25],
    }

    with peewee_db:
        image_prediction = ImagePredictionFactory(
            type="ner",
            model_name="ingredient_detection",
            model_version="ingredient-detection-1.1",
            data={
                "entities": [entity],
            },
            max_confidence=0.9,
        )
        barcode = image_prediction.image.barcode
        server_type = image_prediction.image.server_type
        source_image = image_prediction.image.source_image
        process_ingredient_prediction_job(
            ProductIdentifier(barcode, server_type),
            image_prediction.id,
            source_image=source_image,
        )

    assert import_insights.call_count == 1
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
    assert prediction.source_image == source_image

    assert import_insights.call_args.kwargs == {
        "server_type": server_type,
    }


class TestExtractNutritionJob:
    def generate_nutrition_extraction_prediction(self):
        return NutritionExtractionPrediction(
            entities=NutritionEntities(
                raw=[
                    {
                        "word": "hranite ",
                        "index": 0,
                        "score": 0.9999675750732422,
                        "entity": "O",
                        "char_end": 8,
                        "char_start": 0,
                    }
                ],
                aggregated=[
                    {
                        "end": 15,
                        "worlds": ["883", "kJ"],
                        "score": 0.9993564486503601,
                        "start": 13,
                        "entity": "energy_kj_100g",
                        "char_end": 98,
                        "char_start": 92,
                    }
                ],
                postprocessed=[
                    {
                        "end": 15,
                        "text": "883 kJ",
                        "unit": "kj",
                        "score": 0.9993564486503601,
                        "start": 13,
                        "valid": True,
                        "value": "883",
                        "entity": "energy-kj_100g",
                        "char_end": 98,
                        "char_start": 92,
                    }
                ],
            ),
            nutrients={
                "energy-kj_100g": NutrientPrediction(
                    end=15,
                    text="883 kJ",
                    unit="kj",
                    score=0.9993564486503601,
                    start=13,
                    value="883",
                    entity="energy-kj_100g",
                    char_end=98,
                    char_start=92,
                )
            },
        )

    def test_extract_nutrition_job_image_prediction_exists(self, mocker, peewee_db):
        get_image_from_url_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.get_image_from_url",
        )
        with peewee_db:
            image_model = ImageModelFactory(
                barcode=DEFAULT_BARCODE, source_image=DEFAULT_SOURCE_IMAGE, image_id="1"
            )
            ImagePredictionFactory(
                image=image_model,
                model_name="nutrition_extractor",
                model_version="nutrition_extractor-2.0",
                data={},
                max_confidence=0.9,
                type="nutrition_extraction",
            )
        product_id = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)
        extract_nutrition_job(
            product_id,
            generate_image_url(product_id, DEFAULT_IMAGE_ID),
            generate_json_ocr_url(product_id, DEFAULT_IMAGE_ID),
        )
        assert get_image_from_url_mocker.call_count == 0

    def test_extract_nutrition_job_error_image_download(self, mocker, peewee_db):
        get_image_from_url_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.get_image_from_url", return_value=None
        )
        OCRResult = mocker.patch("robotoff.workers.tasks.import_image.OCRResult")
        OCRResult.from_url.return_value = None
        nutrition_extraction_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.nutrition_extraction"
        )
        with peewee_db:
            ImageModelFactory(
                barcode=DEFAULT_BARCODE, source_image=DEFAULT_SOURCE_IMAGE, image_id="1"
            )
        product_id = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)
        extract_nutrition_job(
            product_id,
            generate_image_url(product_id, DEFAULT_IMAGE_ID),
            generate_json_ocr_url(product_id, DEFAULT_IMAGE_ID),
        )
        assert get_image_from_url_mocker.call_count == 1
        assert get_image_from_url_mocker.call_args.args[0] == generate_image_url(
            product_id, DEFAULT_IMAGE_ID
        )
        assert OCRResult.from_url.call_count == 0
        assert nutrition_extraction_mocker.predict.call_count == 0

    def test_extract_nutrition_job_error_json_ocr_download(self, mocker, peewee_db):
        get_image_from_url_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.get_image_from_url"
        )
        nutrition_extraction_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.nutrition_extraction"
        )
        OCRResult = mocker.patch("robotoff.workers.tasks.import_image.OCRResult")
        OCRResult.from_url.return_value = None
        with peewee_db:
            ImageModelFactory(
                barcode=DEFAULT_BARCODE, source_image=DEFAULT_SOURCE_IMAGE, image_id="1"
            )
        product_id = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)
        extract_nutrition_job(
            product_id,
            generate_image_url(product_id, DEFAULT_IMAGE_ID),
            generate_json_ocr_url(product_id, DEFAULT_IMAGE_ID),
        )
        assert get_image_from_url_mocker.call_count == 1
        assert get_image_from_url_mocker.call_args.args[0] == generate_image_url(
            product_id, DEFAULT_IMAGE_ID
        )
        assert OCRResult.from_url.call_count == 1
        assert OCRResult.from_url.call_args.args[0] == generate_json_ocr_url(
            product_id, DEFAULT_IMAGE_ID
        )
        assert nutrition_extraction_mocker.predict.call_count == 0

    def test_extract_nutrition_job_null_predict_output(self, mocker, peewee_db):
        get_image_from_url_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.get_image_from_url"
        )
        nutrition_extraction_predict_mocker = mocker.patch.object(
            nutrition_extraction_module,
            "predict",
            return_value=None,
        )
        OCRResult = mocker.patch("robotoff.workers.tasks.import_image.OCRResult")
        product_id = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)

        with peewee_db:
            image_model = ImageModelFactory(
                barcode=DEFAULT_BARCODE, source_image=DEFAULT_SOURCE_IMAGE, image_id="1"
            )
            extract_nutrition_job(
                product_id,
                generate_image_url(product_id, DEFAULT_IMAGE_ID),
                generate_json_ocr_url(product_id, DEFAULT_IMAGE_ID),
            )
            assert get_image_from_url_mocker.call_count == 1
            assert OCRResult.from_url.call_count == 1
            assert nutrition_extraction_predict_mocker.call_count == 1
            image_predictions = list(ImagePrediction.select())
            # An image prediction was created
            assert len(image_predictions) == 1
            image_prediction = image_predictions[0]
            assert image_prediction.image == image_model
            assert image_prediction.type == "nutrition_extraction"
            assert image_prediction.model_name == "nutrition_extractor"
            assert image_prediction.model_version == "nutrition_extractor-2.0"
            assert image_prediction.data == {"error": "missing_text"}
            assert image_prediction.max_confidence is None
            assert Prediction.select().count() == 0
            assert ProductInsight.select().count() == 0

    def test_extract_nutrition_job_null_predict_valid_prediction(
        self, mocker, peewee_db
    ):
        get_image_from_url_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.get_image_from_url"
        )
        nutrition_extraction_prediction = (
            self.generate_nutrition_extraction_prediction()
        )
        nutrition_extraction_predict_mocker = mocker.patch.object(
            nutrition_extraction_module,
            "predict",
            return_value=nutrition_extraction_prediction,
        )
        OCRResult = mocker.patch("robotoff.workers.tasks.import_image.OCRResult")
        enqueue_job = mocker.patch("robotoff.workers.tasks.import_image.enqueue_job")
        product_id = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)

        with peewee_db:
            image_model = ImageModelFactory(
                barcode=DEFAULT_BARCODE, source_image=DEFAULT_SOURCE_IMAGE, image_id="1"
            )
            extract_nutrition_job(
                product_id,
                generate_image_url(product_id, DEFAULT_IMAGE_ID),
                generate_json_ocr_url(product_id, DEFAULT_IMAGE_ID),
            )
            assert get_image_from_url_mocker.call_count == 1
            assert OCRResult.from_url.call_count == 1
            assert nutrition_extraction_predict_mocker.call_count == 1
            image_predictions = list(ImagePrediction.select())
            # An image prediction was created
            assert len(image_predictions) == 1
            image_prediction = image_predictions[0]
            assert image_prediction.image == image_model
            assert image_prediction.type == "nutrition_extraction"
            assert image_prediction.model_name == "nutrition_extractor"
            assert image_prediction.model_version == "nutrition_extractor-2.0"
            assert image_prediction.data is not None
            assert set(image_prediction.data.keys()) == {"entities", "nutrients"}
            assert isinstance(image_prediction.data["entities"], dict)
            assert set(image_prediction.data["entities"].keys()) == {
                "raw",
                "aggregated",
                "postprocessed",
            }
            assert isinstance(image_prediction.data["nutrients"], dict)
            assert set(image_prediction.data["nutrients"].keys()) == {
                "energy-kj_100g",
            }
            assert image_prediction.max_confidence == 0.99935645
            # Prediction and insight creation occur during import_insights
            assert Prediction.select().count() == 0
            assert ProductInsight.select().count() == 0

            assert enqueue_job.call_count == 1
            assert len(enqueue_job.call_args.args) == 0
            assert enqueue_job.call_args.kwargs == {
                "func": process_nutrition_prediction_job,
                "queue": get_high_queue(
                    ProductIdentifier(DEFAULT_BARCODE, ServerType.off)
                ),
                "job_kwargs": {"result_ttl": 0},
                "product_id": ProductIdentifier(DEFAULT_BARCODE, ServerType.off),
                "image_prediction_id": image_prediction.id,
                "source_image": image_model.source_image,
            }

    def test_extract_nutrition_job_no_valid_nutrient_extracted(self, mocker, peewee_db):
        mocker.patch("robotoff.workers.tasks.import_image.get_image_from_url")
        nutrition_extraction_prediction = (
            self.generate_nutrition_extraction_prediction()
        )
        nutrition_extraction_prediction.nutrients = {}
        nutrition_extraction_predict_mocker = mocker.patch.object(
            nutrition_extraction_module,
            "predict",
            return_value=nutrition_extraction_prediction,
        )
        mocker.patch("robotoff.workers.tasks.import_image.OCRResult")
        import_insights_mocker = mocker.patch(
            "robotoff.workers.tasks.import_image.import_insights"
        )
        product_id = ProductIdentifier(DEFAULT_BARCODE, ServerType.off)

        with peewee_db:
            image_model = ImageModelFactory(
                barcode=DEFAULT_BARCODE, source_image=DEFAULT_SOURCE_IMAGE, image_id="1"
            )
            extract_nutrition_job(
                product_id,
                generate_image_url(product_id, DEFAULT_IMAGE_ID),
                generate_json_ocr_url(product_id, DEFAULT_IMAGE_ID),
            )
            assert nutrition_extraction_predict_mocker.call_count == 1
            image_predictions = list(ImagePrediction.select())
            # An image prediction was created
            assert len(image_predictions) == 1
            image_prediction = image_predictions[0]
            assert image_prediction.image == image_model
            assert image_prediction.type == "nutrition_extraction"
            assert image_prediction.data is not None
            assert set(image_prediction.data.keys()) == {"entities", "nutrients"}
            assert isinstance(image_prediction.data["entities"], dict)
            assert set(image_prediction.data["entities"].keys()) == {
                "raw",
                "aggregated",
                "postprocessed",
            }
            assert isinstance(image_prediction.data["nutrients"], dict)
            assert image_prediction.data["nutrients"] == {}
            assert image_prediction.max_confidence == 0.99935645
            assert Prediction.select().count() == 0
            assert ProductInsight.select().count() == 0
            assert import_insights_mocker.call_count == 0

    def test_process_nutrition_prediction_job(self, mocker, peewee_db):
        import_insights = mocker.patch(
            "robotoff.workers.tasks.import_image.import_insights"
        )
        data = {
            "entities": {
                "postprocessed": [
                    {
                        "end": 15,
                        "text": "883 kJ",
                        "unit": "kj",
                        "score": 0.9993564486503601,
                        "start": 13,
                        "valid": True,
                        "value": "883",
                        "entity": "energy-kj_100g",
                        "char_end": 98,
                        "char_start": 92,
                    }
                ],
            },
            "nutrients": {
                "energy-kj_100g": {
                    "end": 15,
                    "text": "883 kJ",
                    "unit": "kj",
                    "score": 0.9993564486503601,
                    "start": 13,
                    "value": "883",
                    "entity": "energy-kj_100g",
                    "char_end": 98,
                    "char_start": 92,
                }
            },
        }
        with peewee_db:
            image_prediction = ImagePredictionFactory(
                type="nutrition_extraction",
                model_name="nutrition_extractor",
                model_version="nutrition_extractor-2.0",
                data=data,
                max_confidence=0.99935645,
            )
            source_image = image_prediction.image.source_image
            barcode = image_prediction.image.barcode
            server_type = image_prediction.image.server_type

            process_nutrition_prediction_job(
                ProductIdentifier(barcode, server_type),
                source_image=source_image,
                image_prediction_id=image_prediction.id,
            )

        assert import_insights.call_count == 1
        predictions = import_insights.call_args.args[0]
        assert len(predictions) == 1
        prediction = predictions[0]
        assert prediction.barcode == barcode
        assert prediction.type == PredictionType.nutrient_extraction
        assert prediction.value_tag is None
        assert prediction.value is None
        assert prediction.automatic_processing is False
        assert prediction.predictor == "nutrition_extractor"
        assert prediction.predictor_version == "nutrition_extractor-2.0"
        assert prediction.confidence is None
        assert prediction.source_image == source_image
        assert prediction.server_type == server_type
        assert prediction.data == data


def test_process_created_logos(peewee_db, mocker):
    add_logos_to_ann_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.add_logos_to_ann",
        return_value=None,
    )
    save_nearest_neighbors_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.save_nearest_neighbors",
        return_value=None,
    )
    get_logo_confidence_thresholds_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.get_logo_confidence_thresholds",
        return_value=dict,
    )
    import_logo_insights_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.import_logo_insights",
        return_value=InsightImportResult(),
    )

    with peewee_db:
        image_prediction = ImagePredictionFactory()
        logos = [
            LogoAnnotationFactory(image_prediction=image_prediction, index=i)
            for i in range(5)
        ]
        logo_embeddings = [LogoEmbeddingFactory(logo=logo) for logo in logos]
        process_created_logos(image_prediction.id, DEFAULT_SERVER_TYPE)
        add_logos_to_ann_mock.assert_called()
        mock_call = add_logos_to_ann_mock.mock_calls[0]
        embedding_args = mock_call.args[1]
        server_type = mock_call.args[2]
        assert server_type == DEFAULT_SERVER_TYPE
        assert sorted(embedding_args, key=lambda x: x.logo_id) == logo_embeddings
        save_nearest_neighbors_mock.assert_called()
        get_logo_confidence_thresholds_mock.assert_called()
        import_logo_insights_mock.assert_called()


def test_save_logo_embeddings(peewee_db, mocker):
    expected_embeddings = np.random.rand(5, 512).astype(np.float32)
    generate_clip_embedding_mock = mocker.patch(
        "robotoff.workers.tasks.import_image.generate_clip_embedding",
        return_value=expected_embeddings,
    )
    triton_stub = mocker.MagicMock()

    image_array = np.random.rand(800, 800, 3) * 255
    image = image_array.astype("uint8")
    with peewee_db:
        image_prediction = ImagePredictionFactory()
        logos = [
            LogoAnnotationFactory(image_prediction=image_prediction, index=i)
            for i in range(5)
        ]
        save_logo_embeddings(logos, image, triton_stub)
        logo_embedding_instances = LogoEmbedding.select().where(
            LogoEmbedding.logo_id.in_([logo.id for logo in logos])
        )

        assert len(logo_embedding_instances) == 5
        assert generate_clip_embedding_mock.called
        logo_id_to_logo_embedding = {
            instance.logo_id: instance for instance in logo_embedding_instances
        }

        for i, logo in enumerate(logos):
            assert logo.id in logo_id_to_logo_embedding
            embedding = np.frombuffer(
                logo_id_to_logo_embedding[logo.id].embedding, dtype=np.float32
            ).reshape((1, 512))
            assert (embedding == expected_embeddings[i]).all()
