from robotoff.insights.annotate import (
    NUTRIENT_DEFAULT_UNIT,
    NutrientExtractionAnnotator,
)
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
