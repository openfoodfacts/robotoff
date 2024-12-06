import pytest

from robotoff.prediction.nutrition_extraction import (
    aggregate_entities,
    match_nutrient_value,
    postprocess_aggregated_entities,
    postprocess_aggregated_entities_single,
)


class TestProcessAggregatedEntities:
    def test_postprocess_aggregated_entities_single_entity(self):
        aggregated_entities = [
            {
                "entity": "ENERGY_KCAL_100G",
                "words": ["525", "kcal"],
                "score": 0.99,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 7,
            }
        ]
        expected_output = [
            {
                "entity": "energy-kcal_100g",
                "text": "525 kcal",
                "value": "525",
                "unit": "kcal",
                "score": 0.99,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 7,
                "valid": True,
            }
        ]
        assert postprocess_aggregated_entities(aggregated_entities) == expected_output

    def test_postprocess_aggregated_entities_multiple_entities(self):
        aggregated_entities = [
            {
                "entity": "ENERGY_KCAL_100G",
                "words": ["525", "kcal"],
                "score": 0.99,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 7,
            },
            {
                "entity": "ENERGY_KCAL_100G",
                "words": ["126", "kcal"],
                "score": 0.95,
                "start": 3,
                "end": 5,
                "char_start": 8,
                "char_end": 15,
            },
        ]
        expected_output = [
            {
                "entity": "energy-kcal_100g",
                "text": "525 kcal",
                "value": "525",
                "unit": "kcal",
                "score": 0.99,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 7,
                "valid": False,
                "invalid_reason": "multiple_entities",
            },
            {
                "entity": "energy-kcal_100g",
                "text": "126 kcal",
                "value": "126",
                "unit": "kcal",
                "score": 0.95,
                "start": 3,
                "end": 5,
                "char_start": 8,
                "char_end": 15,
                "valid": False,
                "invalid_reason": "multiple_entities",
            },
        ]
        assert postprocess_aggregated_entities(aggregated_entities) == expected_output

    def test_postprocess_aggregated_entities_no_value(self):
        aggregated_entities = [
            {
                "entity": "SATURATED_FAT_SERVING",
                "words": ["fat"],
                "score": 0.85,
                "start": 0,
                "end": 1,
                "char_start": 0,
                "char_end": 3,
            }
        ]
        expected_output = [
            {
                "entity": "saturated-fat_serving",
                "text": "fat",
                "value": None,
                "unit": None,
                "score": 0.85,
                "start": 0,
                "end": 1,
                "char_start": 0,
                "char_end": 3,
                "valid": False,
            }
        ]
        assert postprocess_aggregated_entities(aggregated_entities) == expected_output

    def test_postprocess_aggregated_entities_trace_value(self):
        aggregated_entities = [
            {
                "entity": "SALT_SERVING",
                "words": ["trace"],
                "score": 0.90,
                "start": 0,
                "end": 1,
                "char_start": 0,
                "char_end": 5,
            }
        ]
        expected_output = [
            {
                "entity": "salt_serving",
                "text": "trace",
                "value": "traces",
                "unit": None,
                "score": 0.90,
                "start": 0,
                "end": 1,
                "char_start": 0,
                "char_end": 5,
                "valid": True,
            }
        ]
        assert postprocess_aggregated_entities(aggregated_entities) == expected_output

    def test_postprocess_aggregated_entities_serving_size(self):
        aggregated_entities = [
            {
                "entity": "SERVING_SIZE",
                "words": ["25", "g"],
                "score": 0.95,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 5,
            }
        ]
        expected_output = [
            {
                "entity": "serving_size",
                "text": "25 g",
                "value": "25 g",
                "unit": None,
                "score": 0.95,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 5,
                "valid": True,
            }
        ]
        assert postprocess_aggregated_entities(aggregated_entities) == expected_output

    def test_postprocess_aggregated_entities_mcg(self):
        aggregated_entities = [
            {
                "entity": "SALT_100G",
                "words": ["1.2", "mcg"],
                "score": 0.95,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 7,
            }
        ]
        expected_output = [
            {
                "entity": "salt_100g",
                "text": "1.2 mcg",
                "value": "1.2",
                "unit": "µg",
                "score": 0.95,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 7,
                "valid": True,
            }
        ]
        assert postprocess_aggregated_entities(aggregated_entities) == expected_output

    def test_postprocess_aggregated_entities_merged_kcal_kj(self):
        aggregated_entities = [
            {
                "entity": "ENERGY_KJ_100G",
                "words": ["525"],
                "score": 0.99,
                "start": 0,
                "end": 1,
                "char_start": 0,
                "char_end": 3,
            },
            {
                "entity": "ENERGY_KCAL_100G",
                "words": ["kj/126", "kcal"],
                "score": 0.99,
                "start": 1,
                "end": 3,
                "char_start": 4,
                "char_end": 15,
            },
        ]
        expected_output = [
            {
                "entity": "energy-kj_100g",
                "text": "525",
                "value": "525",
                "unit": "kj",
                "score": 0.99,
                "start": 0,
                "end": 1,
                "char_start": 0,
                "char_end": 3,
                "valid": True,
            },
            {
                "entity": "energy-kcal_100g",
                "text": "126 kcal",
                "value": "126",
                "unit": "kcal",
                "score": 0.99,
                "start": 1,
                "end": 3,
                "char_start": 4,
                "char_end": 15,
                "valid": True,
            },
        ]
        assert postprocess_aggregated_entities(aggregated_entities) == expected_output


class TestAggregateEntities:
    def test_aggregate_entities_single_entity(self):
        pre_entities = [
            {
                "entity": "ENERGY_KCAL_100G",
                "word": "525",
                "score": 0.99,
                "index": 0,
                "char_start": 0,
                "char_end": 3,
            },
            {
                "entity": "ENERGY_KCAL_100G",
                "word": "KJ",
                "score": 0.99,
                "index": 1,
                "char_start": 4,
                "char_end": 6,
            },
            {
                "entity": "O",
                "word": "matières",
                "score": 0.99,
                "index": 2,
                "char_start": 7,
                "char_end": 15,
            },
        ]
        expected_output = [
            {
                "entity": "ENERGY_KCAL_100G",
                "words": ["525", "KJ"],
                "score": 0.99,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 6,
            }
        ]
        assert aggregate_entities(pre_entities) == expected_output

    def test_aggregate_entities_multiple_entities(self):
        pre_entities = [
            {
                "entity": "SALT_SERVING",
                "word": "0.1",
                "score": 0.99,
                "index": 0,
                "char_start": 0,
                "char_end": 3,
            },
            {
                "entity": "SALT_SERVING",
                "word": "g",
                "score": 0.99,
                "index": 1,
                "char_start": 4,
                "char_end": 5,
            },
            {
                "entity": "PROTEINS_SERVING",
                "word": "101",
                "score": 0.93,
                "index": 2,
                "char_start": 6,
                "char_end": 9,
            },
            {
                "entity": "O",
                "word": "portion",
                "score": 0.99,
                "index": 3,
                "char_start": 10,
                "char_end": 17,
            },
            {
                "entity": "CARBOHYDRATES_SERVING",
                "word": "126",
                "score": 0.91,
                "index": 4,
                "char_start": 18,
                "char_end": 21,
            },
            {
                "entity": "CARBOHYDRATES_SERVING",
                "word": "g",
                "score": 0.95,
                "index": 5,
                "char_start": 22,
                "char_end": 23,
            },
        ]
        expected_output = [
            {
                "entity": "SALT_SERVING",
                "words": ["0.1", "g"],
                "score": 0.99,
                "start": 0,
                "end": 2,
                "char_start": 0,
                "char_end": 5,
            },
            {
                "entity": "PROTEINS_SERVING",
                "words": ["101"],
                "score": 0.93,
                "start": 2,
                "end": 3,
                "char_start": 6,
                "char_end": 9,
            },
            {
                "entity": "CARBOHYDRATES_SERVING",
                "words": ["126", "g"],
                "score": 0.91,
                "start": 4,
                "end": 6,
                "char_start": 18,
                "char_end": 23,
            },
        ]
        assert aggregate_entities(pre_entities) == expected_output


@pytest.mark.parametrize(
    "words_str,entity_label,expected_output",
    [
        ("525 kcal", "energy_kcal_100g", ("525", "kcal", True)),
        ("525 kj", "energy_kj_100g", ("525", "kj", True)),
        ("25 g", "proteins_serving", ("25", "g", True)),
        # Check that the prefix is correctly detected and formatted
        ("<0.5 g", "salt_serving", ("< 0.5", "g", True)),
        ("< 0.5 g", "salt_serving", ("< 0.5", "g", True)),
        # Invalid value
        ("ababa", "proteins_serving", (None, None, False)),
        # Missing unit and value ends with '9' -> infer 'g' as unit and delete '9' digit
        ("25.49", "proteins_serving", ("25.4", "g", True)),
        # Missing unit and value ends with '9', but as only decimal -> keep as it
        ("25.9", "proteins_serving", ("25.9", None, True)),
        # Missing unit and value ends with '9' but not in target entity list
        ("25.9", "iron_100g", ("25.9", None, True)),
        ("O g", "salt_100g", ("0", "g", True)),
        ("O", "salt_100g", ("0", None, True)),
        # Missing unit and value ends with '9' or '8'
        ("0.19", "saturated_fat_100g", ("0.1", "g", True)),
        ("0,18", "saturated_fat_100g", ("0.1", "g", True)),
        ("08", "saturated_fat_100g", ("0", "g", True)),
        ("09", "salt_100g", ("0", "g", True)),
        # Missing unit but value does not end with '8' or '9'
        ("091", "proteins_100g", ("091", None, True)),
    ],
)
def test_match_nutrient_value(words_str: str, entity_label: str, expected_output):

    assert match_nutrient_value(words_str, entity_label) == expected_output


@pytest.mark.parametrize(
    "aggregated_entity,expected_output",
    [
        (
            {
                "end": 90,
                "score": 0.9985358715057373,
                "start": 89,
                "words": ["0,19\n"],
                "entity": "SATURATED_FAT_100G",
                "char_end": 459,
                "char_start": 454,
            },
            {
                "char_end": 459,
                "char_start": 454,
                "end": 90,
                "entity": "saturated-fat_100g",
                "score": 0.9985358715057373,
                "start": 89,
                "text": "0,19",
                "unit": "g",
                "valid": True,
                "value": "0.1",
            },
        ),
        (
            {
                "end": 92,
                "score": 0.9985358715057373,
                "start": 90,
                "words": ["42.5 9"],
                "entity": "SERVING_SIZE",
                "char_end": 460,
                "char_start": 454,
            },
            {
                "char_end": 460,
                "char_start": 454,
                "end": 92,
                "entity": "serving_size",
                "score": 0.9985358715057373,
                "start": 90,
                "text": "42.5 9",
                "unit": None,
                "valid": True,
                "value": "42.5 g",
            },
        ),
    ],
)
def test_postprocess_aggregated_entities_single(aggregated_entity, expected_output):
    assert postprocess_aggregated_entities_single(aggregated_entity) == expected_output
