from robotoff.prediction.category.neural.keras_category_classifier_3_0.preprocessing import (
    generate_nutrition_input_dict,
)

product_1 = {
    "schema_version": 1003,
    "nutrition": {
        "aggregated_set": {
            "nutrients": {
                "carbohydrates": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 46,
                },
                "energy": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "kJ",
                    "value": 1396,
                    "value_computed": 1396,
                },
                "energy-kcal": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "kcal",
                    "value": 333,
                    "value_computed": 333,
                },
                "energy-kj": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "kJ",
                    "value": 1396,
                    "value_computed": 1396,
                },
                "fat": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 5,
                },
                "fiber": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 26,
                },
                "fruits-vegetables-nuts": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "%",
                    "value": 0,
                },
                "proteins": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 13,
                },
                "salt": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 1.2,
                    "value_computed": 1.2,
                },
                "saturated-fat": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 1,
                },
                "sodium": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 0.48,
                    "value_computed": 0.48,
                },
                "sugars": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 2,
                },
                "water": {
                    "modifier": "~",
                    "source": "estimate",
                    "source_index": 1,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 9.51355791666667,
                },
            },
            "per": "100g",
            "preparation": "as_sold",
        },
        # No need for input sets here, so we remove it to keep the declaration concise
        "input_sets": [],
    },
}

product_2 = {
    "schema_version": 1003,
    "nutrition": {
        "aggregated_set": {
            "nutrients": {
                "energy": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "kJ",
                    "value": 1396,
                    "value_computed": 1396,
                },
                "energy-kcal": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "kcal",
                    # value is obviously wrong here
                    "value": 5000,
                    "value_computed": 5000,
                },
                "energy-kj": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "kJ",
                    "value": 1396,
                    "value_computed": 1396,
                },
                "fat": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    # Value is wrong here
                    "value": -10,
                },
                "fiber": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 26,
                },
                "fruits-vegetables-nuts": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "%",
                    "value": 0,
                },
                "proteins": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    # value is obviously wrong here
                    "value": 120,
                },
                "salt": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 1.2,
                    "value_computed": 1.2,
                },
                "saturated-fat": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 1,
                },
                "sodium": {
                    "source": "packaging",
                    "source_index": 0,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 0.48,
                    "value_computed": 0.48,
                },
                "water": {
                    "modifier": "~",
                    "source": "estimate",
                    "source_index": 1,
                    "source_per": "100g",
                    "unit": "g",
                    "value": 9.51355791666667,
                },
            },
            "per": "100g",
            "preparation": "as_sold",
        },
        # No need for input sets here, so we remove it to keep the declaration concise
        "input_sets": [],
    },
}


def test_generate_nutrition_input_dict():
    """Test with new nutrition schema (schema version 1003)."""
    output = generate_nutrition_input_dict(product_1)
    assert output == {
        "carbohydrates": 46.0,
        "energy_kcal": 333.0,
        "fat": 5.0,
        "fiber": 26.0,
        "fruits_vegetables_nuts": 0.0,
        "proteins": 13.0,
        "salt": 1.2,
        "saturated_fat": 1.0,
        "sugars": 2.0,
    }


def test_generate_nutrition_input_dict_null_aggregated_set():
    """Test with new nutrition schema (schema version 1003)."""
    output = generate_nutrition_input_dict(
        {
            "schema_version": 1003,
            "nutrition": {
                "aggregated_set": None,
                "input_sets": [],
            },
        }
    )
    assert output == {
        "carbohydrates": -1,
        "energy_kcal": -1,
        "fat": -1,
        "fiber": -1,
        "fruits_vegetables_nuts": -1,
        "proteins": -1,
        "salt": -1,
        "saturated_fat": -1,
        "sugars": -1,
    }


def test_generate_nutrition_input_dict_legacy_schema():
    """Test with legacy schema, we don't support it anymore, we expect an empty dict."""
    output = generate_nutrition_input_dict(
        {
            "product": {
                "nutriments": {
                    "energy-kcal_100g": 333,
                    "fat_100g": 5.0,
                    "proteins_100g": 13.0,
                }
            }
        }
    )
    assert output == {
        "carbohydrates": -1,
        "energy_kcal": -1,
        "fat": -1,
        "fiber": -1,
        "fruits_vegetables_nuts": -1,
        "proteins": -1,
        "salt": -1,
        "saturated_fat": -1,
        "sugars": -1,
    }


def test_generate_nutrition_input_dict_missing_or_wrong_values():
    """Test the processing function, by providing:

    - some missing values
    - some out of range values
    """
    output = generate_nutrition_input_dict(product_2)
    assert output == {
        "carbohydrates": -1,
        "energy_kcal": -2,
        "fat": -2,
        "fiber": 26.0,
        "fruits_vegetables_nuts": 0.0,
        "proteins": -2,
        "salt": 1.2,
        "saturated_fat": 1.0,
        "sugars": -1,
    }
