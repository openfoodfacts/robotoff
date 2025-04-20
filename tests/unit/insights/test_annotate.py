from robotoff.insights.annotate import (
    NUTRIENT_DEFAULT_UNIT,
    UPDATED_ANNOTATION_RESULT,
    ImageOrientationAnnotator,
    NutrientExtractionAnnotator,
)
from robotoff.models import ProductInsight
from robotoff.types import NutrientData, NutrientSingleValue


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


class TestImageOrientationAnnotator:
    def test_process_annotation(self, mocker):
        mock_select_rotate_image = mocker.patch(
            "robotoff.insights.annotate.select_rotate_image"
        )
        mock_get_product = mocker.patch(
            "robotoff.insights.annotate.get_product",
            return_value={"images": {"2": {"sizes": {"full": {"w": 1000, "h": 2000}}}}},
        )

        insight = ProductInsight(
            id="123e4567-e89b-12d3-a456-426614174000",
            type="image_orientation",
            source_image="/12/345/6789/2.jpg",
            data={
                "rotation": 270,
                "orientation": "right",
                "orientation_fraction": 0.95,
            },
            barcode="3760094310634",
            server_type="off",
        )

        result = ImageOrientationAnnotator.process_annotation(insight)
        mock_get_product.assert_called_once()
        mock_select_rotate_image.assert_called_once_with(
            product_id=insight.get_product_id(),
            image_id="2",
            image_key="2",
            rotate=270,
            crop_bounding_box=None,
            auth=None,
            is_vote=False,
            insight_id=insight.id,
        )

        assert result == UPDATED_ANNOTATION_RESULT
