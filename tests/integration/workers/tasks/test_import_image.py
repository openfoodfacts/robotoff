import pytest

from robotoff.models import ImagePrediction, Prediction, ProductInsight
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
from robotoff.types import PredictionType, ProductIdentifier, ServerType
from robotoff.workers.tasks.import_image import (
    extract_ingredients_job,
    extract_nutrition_job,
)
from robotoff.workers.tasks.import_image import (
    nutrition_extraction as nutrition_extraction_module,
)

from ...models_utils import ImageModelFactory, ImagePredictionFactory, clean_db

DEFAULT_BARCODE = "1234567890123"
DEFAULT_IMAGE_ID = "1"
DEFAULT_SOURCE_IMAGE = "/123/456/789/0123/1.jpg"


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

            assert import_insights_mocker.call_count == 1
            args = import_insights_mocker.call_args.args
            assert len(args) == 1
            predictions = args[0]
            assert len(predictions) == 1
            prediction = predictions[0]
            assert prediction.barcode == DEFAULT_BARCODE
            assert prediction.type == PredictionType.nutrient_extraction
            assert prediction.value_tag is None
            assert prediction.value is None
            assert prediction.automatic_processing is False
            assert prediction.predictor == "nutrition_extractor"
            assert prediction.predictor_version == "nutrition_extractor-2.0"
            assert prediction.confidence is None
            assert prediction.source_image == DEFAULT_SOURCE_IMAGE
            assert prediction.server_type == ServerType.off
            assert prediction.data == {
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
