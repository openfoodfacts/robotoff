NUTRITION_1 = {
    "aggregated_set": {
        "nutrients": {
            "salt": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "serving",
                "unit": "g",
                "value": 0.5,
            },
            "saturated-fat": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "serving",
                "unit": "g",
                "value": 0.5,
            },
        },
        "per": "100g",
        "preparation": "as_sold",
    },
    "input_sets": [
        {
            "nutrients": {
                "salt": {"unit": "g", "value": 1, "value_string": "1"},
                "saturated-fat": {
                    "unit": "g",
                    "value": 1,
                    "value_string": "1",
                },
            },
            "per": "serving",
            "per_quantity": 200,
            "per_unit": "g",
            "preparation": "as_sold",
            "source": "packaging",
        }
    ],
}

NUTRITION_2 = {
    "aggregated_set": {
        "nutrients": {
            "salt": {
                "modifier": "<=",
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 5,
            },
            "sodium": {
                "modifier": "<=",
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 2,
            },
            "sugars": {
                "source": "usda",
                "source_index": 1,
                "source_per": "100g",
                "unit": "g",
                "value": 5.2,
            },
        },
        "per": "100g",
        "preparation": "as_sold",
    },
    "input_sets": [
        {
            "nutrients": {
                "sodium": {
                    "modifier": "<=",
                    "unit": "g",
                    "value": 2,
                    "value_string": "2.0",
                }
            },
            "per": "100g",
            "per_quantity": "100",
            "per_unit": "g",
            "preparation": "as_sold",
            "source": "packaging",
        },
        {
            "nutrients": {
                "sodium": {
                    "unit": "g",
                    "value": 0.1,
                    "value_string": "0.1",
                },
                "sugars": {
                    "unit": "g",
                    "value": 5.2,
                    "value_string": "5.2",
                },
            },
            "per": "100g",
            "per_quantity": "100",
            "per_unit": "g",
            "preparation": "as_sold",
            "source": "usda",
        },
    ],
}


# With `value_computed` in the input_set
NUTRITION_3 = {
    "aggregated_set": {
        "nutrients": {
            "carbohydrates": {
                "modifier": "<",
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 0.5,
            },
            "energy": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "kJ",
                "value": 332,
                "value_computed": 340.4,
            },
            "energy-kcal": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "kcal",
                "value": 78,
                "value_computed": 80.3,
            },
            "energy-kj": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "kJ",
                "value": 332,
                "value_computed": 340.4,
            },
            "fat": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 0.7,
            },
            "proteins": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 18,
            },
            "salt": {
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 1.2,
            },
            "saturated-fat": {
                "modifier": "<",
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 0.1,
            },
            "sodium": {
                "modifier": "~",
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 0.48,
            },
            "sugars": {
                "modifier": "<",
                "source": "packaging",
                "source_index": 0,
                "source_per": "100g",
                "unit": "g",
                "value": 0.5,
            },
        },
        "per": "100g",
        "preparation": "as_sold",
    },
    "input_sets": [
        {
            "nutrients": {
                "carbohydrates": {
                    "modifier": "<",
                    "unit": "g",
                    "value": 0.5,
                    "value_string": "0.5",
                },
                "energy-kcal": {
                    "unit": "kcal",
                    "value": 78,
                    "value_computed": 80.3,
                    "value_string": "78",
                },
                "energy-kj": {
                    "unit": "kJ",
                    "value": 332,
                    "value_computed": 340.4,
                    "value_string": "332",
                },
                "fat": {"unit": "g", "value": 0.7, "value_string": "0.7"},
                "proteins": {"unit": "g", "value": 18, "value_string": "18"},
                "salt": {"unit": "g", "value": 1.2, "value_string": "1.2"},
                "saturated-fat": {
                    "modifier": "<",
                    "unit": "g",
                    "value": 0.1,
                    "value_string": "0.1",
                },
                "sodium": {"unit": "g", "value_computed": 0.48},
                "sugars": {
                    "modifier": "<",
                    "unit": "g",
                    "value": 0.5,
                    "value_string": "0.5",
                },
            },
            "per": "100g",
            "per_quantity": 100,
            "per_unit": "g",
            "preparation": "as_sold",
            "source": "packaging",
            "unspecified_nutrients": ["fiber"],
        }
    ],
}
