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
