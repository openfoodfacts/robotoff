from typing import Dict, List

import pytest

from robotoff.prediction.category.matcher import match, predict, process
from robotoff.prediction.types import Prediction, PredictionType
from robotoff.taxonomy import get_taxonomy


@pytest.mark.parametrize(
    "text,lang,expected",
    [
        ("Filets de POULET", "fr", "filet poulet"),
        ("poulets au curry", "fr", "poulet curry"),
        ("Mélange quatre épices", "fr", "melanger quatre epice"),
        ("of", "en", ""),  # of is a stop word in en
    ],
)
def test_process(text: str, lang: str, expected: str):
    assert process(text, lang) == expected


@pytest.mark.parametrize(
    "text,lang,expected",
    [
        (
            "Filets de POULET bio de provence",
            "fr",
            ["en:chicken-breasts"],
        ),
        ("poulets au curry épicé", "fr", ["en:chicken-curry"]),
        (
            "yaourt nature et riz au lait",
            "fr",
            ["en:plain-yogurts", "en:rice-puddings"],
        ),
        ("Sprite", "fr", []),  # no category named sprite
        (
            "Sirop de mangue",
            "fr",
            ["en:mango-syrups"],
        ),
        ("Lardons pauvres en sel", "fr", ["en:lardons"]),
        ("miels Méditérannée", "fr", ["en:mediterannean-honeys"]),
        ("yaourt nature", "fr", ["en:plain-yogurts"]),
        ("eaux de sources Cristaline 1,5L", "fr", ["en:spring-waters"]),
        ("crème dessert vanille", "fr", ["fr:cremes-dessert-vanille"]),
        ("UNKNOWN", "en", []),
        ("PARIS Brest", "en", ["en:paris-brest"]),
        ("Asian Chicken Salad", "en", []),
        ("Chorizo de pavo", "es", ["en:chorizo"]),
        ("Pollo limpio", "es", ["en:chickens"]),
    ],
)
def test_match(text: str, lang: str, expected: List[str], mocker):
    mocker.patch(
        "robotoff.prediction.category.matcher.get_taxonomy",
        return_value=get_taxonomy("category", offline=True),
    )
    results = match(text, lang)
    assert [result[0] for result in results] == expected


@pytest.mark.parametrize(
    "lang,product_name,expected_value_tag,expected_pattern,additional_data",
    [
        (
            "fr",
            "Aiguillettes de canard du pays basque",
            "fr:aiguillettes-de-canard",
            "aiguillette canard",
            {
                "is_full_match": False,
                "processed_product_name": "aiguillette canard pays basque",
                "start_idx": 0,
                "end_idx": 18,
                "category_name": "Aiguillettes de canard",
            },
        ),
        # More than one category matching this query so no result should be
        # returned
        ("fr", "yaourt nature et riz au lait", None, None, {}),
    ],
)
def test_predict(
    lang: str,
    product_name: str,
    expected_value_tag: str,
    expected_pattern: str,
    additional_data: Dict,
):
    product = {
        f"product_name_{lang}": product_name,
        "languages_codes": [lang],
    }
    predictions = predict(product)

    if expected_value_tag is None:
        assert len(predictions) == 0
    else:
        prediction = predictions[0]
        assert isinstance(prediction, Prediction)
        assert prediction.type == PredictionType.category.name
        assert prediction.value_tag == expected_value_tag
        assert prediction.predictor == "matcher"
        assert prediction.data == {
            "pattern": expected_pattern,
            "product_name": product_name,
            "lang": lang,
            **additional_data,
        }
        assert prediction.automatic_processing is False
