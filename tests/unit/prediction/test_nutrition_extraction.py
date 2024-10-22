from robotoff.prediction.nutrition_extraction import (
    aggregate_entities,
    postprocess_aggregated_entities,
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
                "entity": "energy_kcal_100g",
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
                "entity": "energy_kcal_100g",
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
                "entity": "energy_kcal_100g",
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
                "entity": "FAT_SERVING",
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
                "entity": "fat_serving",
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
                "entity": "energy_kj_100g",
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
                "entity": "energy_kcal_100g",
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
