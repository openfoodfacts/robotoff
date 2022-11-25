import pytest

from robotoff.prediction.ocr.packaging import find_packaging, match_packaging
from robotoff.prediction.types import Prediction, PredictionType


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", []),
        ("random text!", []),
        ("  ", []),
        ("packaaaa", []),  # pack shouldn't match (check negative lookahead)
        ("testetui", []),  # etui shouldn't match (check negative lookbehind)
        ("étui", [{"shape": {"value": "etui", "value_tag": "en:sleeve"}}]),
        (
            "étui EN  carton à recycler",
            [
                {
                    "shape": {"value": "etui", "value_tag": "en:sleeve"},
                    "material": {"value": "carton", "value_tag": "en:cardboard"},
                    "recycling": {"value": "recycler", "value_tag": "en:recycle"},
                }
            ],
        ),
        (
            "bouteille en plastique pet",
            [
                {
                    "shape": {"value": "bouteille", "value_tag": "en:bottle"},
                    "material": {
                        "value": "pet",
                        "value_tag": "en:pet-polyethylene-terephthalate",
                    },
                }
            ],
        ),
        (
            "BOUTEILLE en verre sombre et son bouchon en aluminium à jeter",
            [
                {
                    "shape": {"value": "bouteille", "value_tag": "en:bottle"},
                    "material": {
                        "value": "verre sombre",
                        "value_tag": "en:dark-sort-glass",
                    },
                },
                {
                    "shape": {"value": "bouchon", "value_tag": "en:bottle-cap"},
                    "material": {
                        "value": "aluminium",
                        "value_tag": "en:aluminium",
                    },
                    "recycling": {
                        "value": "jeter",
                        "value_tag": "en:discard",
                    },
                },
            ],
        ),
        (
            "Bouteille verre à recycler / Bouchon liège à jeter",
            [
                {
                    "material": {"value": "verre", "value_tag": "en:glass"},
                    "recycling": {"value": "recycler", "value_tag": "en:recycle"},
                    "shape": {"value": "bouteille", "value_tag": "en:bottle"},
                },
                {
                    "material": {"value": "liege", "value_tag": "en:cork"},
                    "recycling": {"value": "jeter", "value_tag": "en:discard"},
                    "shape": {"value": "bouchon", "value_tag": "en:bottle-cap"},
                },
            ],
        ),
    ],
)
def test_match_packaging(text: str, expected: list[dict]):
    assert match_packaging(text) == expected


@pytest.mark.parametrize(
    "text,expected_prediction_data",
    [
        (
            "Packaging: boîte carton,...",
            [
                {
                    "lang": "fr",
                    "element": {
                        "shape": {"value": "boite", "value_tag": "en:box"},
                        "material": {
                            "value": "carton",
                            "value_tag": "en:cardboard",
                        },
                    },
                }
            ],
        ),
        (
            "opercule en métal à recycler; boîte en PET à recycler, filet plastique à JETER, fruits à coque, coque en métal",
            [
                {
                    "lang": "fr",
                    "element": {
                        "shape": {"value": "opercule", "value_tag": "en:seal"},
                        "material": {"value": "metal", "value_tag": "en:metal"},
                        "recycling": {"value": "recycler", "value_tag": "en:recycle"},
                    },
                },
                {
                    "lang": "fr",
                    "element": {
                        "shape": {"value": "boite", "value_tag": "en:box"},
                        "material": {
                            "value": "pet",
                            "value_tag": "en:pet-polyethylene-terephthalate",
                        },
                        "recycling": {"value": "recycler", "value_tag": "en:recycle"},
                    },
                },
                {
                    "lang": "fr",
                    "element": {
                        "shape": {"value": "filet", "value_tag": "en:net"},
                        "material": {"value": "plastique", "value_tag": "en:plastic"},
                        "recycling": {"value": "jeter", "value_tag": "en:discard"},
                    },
                },
                {
                    "lang": "fr",
                    "element": {
                        "shape": {"value": "coque", "value_tag": "en:tray"},
                        "material": {"value": "metal", "value_tag": "en:metal"},
                    },
                },
            ],
        ),
        ("Ingrédients: 100% tomate", []),
        ("", []),
    ],
)
def test_find_packaging(text: str, expected_prediction_data: list[dict]):
    predictions = find_packaging(text)
    assert len(predictions) == len(expected_prediction_data)

    for prediction, expected_data in zip(predictions, expected_prediction_data):
        assert isinstance(prediction, Prediction)
        assert prediction.type is PredictionType.packaging
        assert prediction.automatic_processing is False
        assert prediction.data == expected_data
