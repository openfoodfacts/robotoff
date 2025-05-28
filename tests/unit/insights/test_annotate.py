from robotoff.insights.annotate import (
    CANNOT_VOTE_RESULT,
    INVALID_DATA,
    MISSING_PRODUCT_RESULT,
    NUTRIENT_DEFAULT_UNIT,
    UPDATED_ANNOTATION_RESULT,
    IngredientDetectionAnnotator,
    NutrientExtractionAnnotator,
    rotate_bounding_box,
)
from robotoff.models import ProductInsight
from robotoff.types import (
    InsightType,
    JSONType,
    NutrientData,
    NutrientSingleValue,
    ProductIdentifier,
    ServerType,
)

DEFAULT_BARCODE = "3760094310634"
DEFAULT_SOURCE_IMAGE = "/376/009/431/0634/1.jpg"
DEFAULT_SERVER_TYPE = ServerType.off
DEFAULT_PRODUCT_ID = ProductIdentifier(DEFAULT_BARCODE, DEFAULT_SERVER_TYPE)


class TestNutrientExtractionAnnotator:
    def test_add_default_unit_with_missing_units(self):
        nutrients = {
            "energy-kcal_100g": NutrientSingleValue(value="100", unit=None),
            "proteins_100g": NutrientSingleValue(value="10", unit=None),
            "sugars_100g": NutrientSingleValue(value="5", unit=None),
        }
        nutrient_data = NutrientData(nutrients=nutrients)
        result = NutrientExtractionAnnotator.add_default_unit(nutrient_data)

        assert (
            result.nutrients["energy-kcal"].unit == NUTRIENT_DEFAULT_UNIT["energy-kcal"]
        )
        assert result.nutrients["proteins"].unit == NUTRIENT_DEFAULT_UNIT["proteins"]
        assert result.nutrients["sugars"].unit == NUTRIENT_DEFAULT_UNIT["sugars"]

    def test_add_default_unit_with_existing_units(self):
        nutrients = {
            "energy-kcal_serving": NutrientSingleValue(value="100", unit="kcal"),
            "proteins_serving": NutrientSingleValue(value="10", unit="g"),
            "sugars_serving": NutrientSingleValue(value="5", unit="g"),
        }
        nutrient_data = NutrientData(nutrients=nutrients, serving_size="100 g")
        result = NutrientExtractionAnnotator.add_default_unit(nutrient_data)

        assert result.nutrients["energy-kcal"].unit == "kcal"
        assert result.nutrients["proteins"].unit == "g"
        assert result.nutrients["sugars"].unit == "g"
        assert result.serving_size == "100 g"

    def test_add_default_unit_with_mixed_units(self):
        nutrients = {
            "energy-kcal_100g": NutrientSingleValue(value="100", unit=None),
            "proteins_100g": NutrientSingleValue(value="10", unit="mg"),
            "sugars_100g": NutrientSingleValue(value="5", unit=None),
        }
        nutrient_data = NutrientData(nutrients=nutrients)
        result = NutrientExtractionAnnotator.add_default_unit(nutrient_data)

        assert (
            result.nutrients["energy-kcal"].unit == NUTRIENT_DEFAULT_UNIT["energy-kcal"]
        )
        assert result.nutrients["proteins"].unit == "mg"
        assert result.nutrients["sugars"].unit == NUTRIENT_DEFAULT_UNIT["sugars"]

    def test_add_default_unit_with_no_default_unit(self):
        nutrients = {
            "unknown-nutrient_100g": NutrientSingleValue(value="100", unit=None),
        }
        nutrient_data = NutrientData(nutrients=nutrients)
        result = NutrientExtractionAnnotator.add_default_unit(nutrient_data)

        assert result.nutrients["unknown-nutrient"].unit is None


class TestIngredientDetectionAnnotator:
    @staticmethod
    def _create_product_insight(
        data: JSONType,
        value_tag: str = "en",
        confidence: float = 0.9,
        source_image: str = DEFAULT_SOURCE_IMAGE,
        barcode: str = DEFAULT_BARCODE,
        server_type: ServerType = DEFAULT_SERVER_TYPE,
    ) -> ProductInsight:
        bounding_box = data["bounding_box"]
        return ProductInsight(
            data=data,
            barcode=barcode,
            type=InsightType.ingredient_detection,
            value_tag=value_tag,
            value=None,
            source_image=source_image,
            server_type=server_type,
            predictor="ingredient_detection",
            predictor_version="ingredient-detection-1.1",
            confidence=confidence,
            bounding_box=bounding_box,
        )

    def test_select_ingredient_image_missing_image(self, mocker):
        select_rotate_image = mocker.patch(
            "robotoff.insights.annotate.select_rotate_image"
        )
        get_image_rotation = mocker.patch(
            "robotoff.insights.annotate.get_image_rotation", return_value=0
        )
        insight = self._create_product_insight(
            data={"bounding_box": [0.1, 0.1, 0.5, 0.5]}
        )
        product = {
            "code": DEFAULT_BARCODE,
        }
        IngredientDetectionAnnotator.select_ingredient_image(
            insight, product, has_user_annotation=False
        )
        assert select_rotate_image.call_count == 0
        assert get_image_rotation.call_count == 0

    def test_select_ingredient_image_with_cropping(self, mocker):
        select_rotate_image = mocker.patch(
            "robotoff.insights.annotate.select_rotate_image"
        )
        get_image_rotation = mocker.patch(
            "robotoff.insights.annotate.get_image_rotation", return_value=0
        )
        insight = self._create_product_insight(
            data={"bounding_box": [0.1, 0.1, 0.5, 0.5]}
        )
        product = {
            "code": DEFAULT_BARCODE,
            "images": {
                "1": {
                    "sizes": {
                        "full": {
                            "w": 1000,
                            "h": 800,
                        }
                    }
                }
            },
        }
        IngredientDetectionAnnotator.select_ingredient_image(
            insight, product, has_user_annotation=False
        )
        assert select_rotate_image.call_count == 1
        assert select_rotate_image.call_args.args == ()
        assert select_rotate_image.call_args.kwargs == {
            "product_id": DEFAULT_PRODUCT_ID,
            "rotate": 0,
            "is_vote": False,
            "insight_id": insight.id,
            "image_key": "ingredients_en",
            "image_id": "1",
            "crop_bounding_box": (80.0, 100.0, 400.0, 500.0),
            "auth": None,
        }

        assert get_image_rotation.call_count == 1
        assert get_image_rotation.call_args.args == (insight.source_image,)

    def test_select_ingredient_image_with_cropping_and_rotation(self, mocker):
        select_rotate_image = mocker.patch(
            "robotoff.insights.annotate.select_rotate_image"
        )
        get_image_rotation = mocker.patch(
            "robotoff.insights.annotate.get_image_rotation", return_value=90
        )
        insight = self._create_product_insight(
            data={"bounding_box": [0.1, 0.1, 0.5, 0.5]}
        )
        product = {
            "code": DEFAULT_BARCODE,
            "images": {
                "1": {
                    "sizes": {
                        "full": {
                            "w": 1000,
                            "h": 800,
                        }
                    }
                }
            },
        }
        IngredientDetectionAnnotator.select_ingredient_image(
            insight, product, has_user_annotation=False
        )
        assert select_rotate_image.call_count == 1
        assert select_rotate_image.call_args.args == ()
        assert select_rotate_image.call_args.kwargs == {
            "product_id": DEFAULT_PRODUCT_ID,
            "rotate": 90,
            "is_vote": False,
            "insight_id": insight.id,
            "image_key": "ingredients_en",
            "image_id": "1",
            "crop_bounding_box": (100.0, 400.0, 500.0, 720.0),
            "auth": None,
        }

        assert get_image_rotation.call_count == 1
        assert get_image_rotation.call_args.args == (insight.source_image,)

    def test_select_ingredient_image_image_already_selected_with_no_cropping_information(
        self, mocker
    ):
        select_rotate_image = mocker.patch(
            "robotoff.insights.annotate.select_rotate_image"
        )
        get_image_rotation = mocker.patch(
            "robotoff.insights.annotate.get_image_rotation", return_value=0
        )
        insight = self._create_product_insight(
            data={"bounding_box": [0.1, 0.1, 0.5, 0.5]}
        )
        product = {
            "code": DEFAULT_BARCODE,
            "images": {
                "1": {
                    "sizes": {
                        "full": {
                            "w": 1000,
                            "h": 800,
                        }
                    }
                },
                "ingredients_en": {
                    "imgid": "1",
                },
            },
        }
        IngredientDetectionAnnotator.select_ingredient_image(
            insight,
            product,
            # Set has_user_annotation to True so that no cropping is needed
            has_user_annotation=True,
        )
        assert select_rotate_image.call_count == 0
        assert get_image_rotation.call_count == 1
        assert get_image_rotation.call_args.args == (insight.source_image,)

    def test_process_annotation_no_data(self, mocker):
        save_ingredients = mocker.patch("robotoff.insights.annotate.save_ingredients")
        select_ingredient_image = mocker.patch(
            "robotoff.insights.annotate.IngredientDetectionAnnotator.select_ingredient_image"
        )
        get_product = mocker.patch(
            "robotoff.insights.annotate.get_product",
            return_value={"code": DEFAULT_BARCODE},
        )
        ingredients_text = "Water, salt"
        lang = "fr"
        insight = self._create_product_insight(
            data={"text": ingredients_text, "bounding_box": [0.1, 0.1, 0.5, 0.5]},
            value_tag=lang,
        )
        annotation_result = IngredientDetectionAnnotator.process_annotation(
            insight, data=None
        )
        assert annotation_result is UPDATED_ANNOTATION_RESULT

        assert get_product.call_count == 1
        assert get_product.call_args.args == (DEFAULT_PRODUCT_ID, ["code", "images"])
        assert save_ingredients.call_count == 1
        assert save_ingredients.call_args.args == ()
        assert save_ingredients.call_args.kwargs == {
            "product_id": DEFAULT_PRODUCT_ID,
            "auth": None,
            "insight_id": insight.id,
            "ingredient_text": ingredients_text,
            "lang": lang,
            "is_vote": False,
        }

        assert select_ingredient_image.call_count == 1
        assert select_ingredient_image.call_args.args == (
            insight,
            {"code": DEFAULT_BARCODE},
        )
        assert select_ingredient_image.call_args.kwargs == {
            "has_user_annotation": False,
            "auth": None,
        }

    def test_process_annotation_with_data(self, mocker):
        save_ingredients = mocker.patch("robotoff.insights.annotate.save_ingredients")
        select_ingredient_image = mocker.patch(
            "robotoff.insights.annotate.IngredientDetectionAnnotator.select_ingredient_image"
        )
        get_product = mocker.patch(
            "robotoff.insights.annotate.get_product",
            return_value={"code": DEFAULT_BARCODE},
        )
        ingredients_text = "Water, salt"
        ingredients_text_updated = "Bread, corn, salt"
        lang = "it"
        insight = self._create_product_insight(
            data={"text": ingredients_text, "bounding_box": [0.1, 0.1, 0.5, 0.5]},
            value_tag=lang,
        )
        insight.save = mocker.MagicMock()

        annotation_result = IngredientDetectionAnnotator.process_annotation(
            insight, data={"annotation": ingredients_text_updated}
        )
        assert annotation_result is UPDATED_ANNOTATION_RESULT

        assert get_product.call_count == 1
        assert save_ingredients.call_count == 1
        assert save_ingredients.call_args.args == ()
        assert save_ingredients.call_args.kwargs == {
            "product_id": DEFAULT_PRODUCT_ID,
            "auth": None,
            "insight_id": insight.id,
            "ingredient_text": ingredients_text_updated,
            "lang": lang,
            "is_vote": False,
        }
        assert select_ingredient_image.call_count == 1
        assert insight.save.call_count == 1

    def test_process_annotation_missing_product(self, mocker):
        get_product = mocker.patch(
            "robotoff.insights.annotate.get_product",
            return_value=None,
        )
        ingredients_text = "Water, salt"
        insight = self._create_product_insight(
            data={"text": ingredients_text, "bounding_box": [0.1, 0.1, 0.5, 0.5]}
        )

        annotation_result = IngredientDetectionAnnotator.process_annotation(
            insight, data=None
        )
        assert annotation_result is MISSING_PRODUCT_RESULT

        assert get_product.call_count == 1

    def test_process_annotation_is_vote(self):
        ingredients_text = "Water, salt"
        insight = self._create_product_insight(
            data={"text": ingredients_text, "bounding_box": [0.1, 0.1, 0.5, 0.5]}
        )

        annotation_result = IngredientDetectionAnnotator.process_annotation(
            insight, data=None, is_vote=True
        )
        assert annotation_result is CANNOT_VOTE_RESULT

    def test_process_annotation_invalid_data(self):
        ingredients_text = "Water, salt"
        insight = self._create_product_insight(
            data={"text": ingredients_text, "bounding_box": [0.1, 0.1, 0.5, 0.5]}
        )

        annotation_result = IngredientDetectionAnnotator.process_annotation(
            insight, data={"invalid_field": "Test"}, is_vote=False
        )
        assert annotation_result is INVALID_DATA


def test_rotate_bounding_box():
    bounding_box = (10, 20, 100, 200)
    width, height = 1000, 800
    result = rotate_bounding_box(bounding_box, width, height, 0)
    assert result == (10, 20, 100, 200)

    result = rotate_bounding_box(bounding_box, width, height, 90)
    assert result == (20, 800 - 100, 200, 800 - 10)

    result = rotate_bounding_box(bounding_box, width, height, 180)
    assert result == (800 - 100, 1000 - 200, 800 - 10, 1000 - 20)

    result = rotate_bounding_box(bounding_box, width, height, 270)
    assert result == (1000 - 200, 10, 1000 - 20, 100)
