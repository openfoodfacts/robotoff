import pytest
from openfoodfacts.types import TaxonomyType

from robotoff.taxonomy import get_taxonomy
from robotoff.workers.tasks.import_image import (
    add_ingredient_in_taxonomy_field,
    get_text_from_bounding_box,
)

from ...pytest_utils import get_ocr_result_asset


@pytest.mark.parametrize(
    "ocr_asset_path, bounding_box, image_width, image_height, expected_text",
    [
        (
            "/main/robotoff/tests/unit/ocr/5400910301160_1.json",
            (
                0.2808293402194977,
                0.37121888995170593,
                0.35544055700302124,
                0.49409016966819763,
            ),
            882,
            1200,
            "NUTRIDIA ",
        ),
        (
            "/main/robotoff/tests/unit/ocr/9421023629015_5.json",
            (0.342327416, 0.469950765, 0.512927711, 0.659323752),
            901,
            1200,
            "manuka health\nNEW ZEALAND\n",
        ),
    ],
)
def test_get_text_from_bounding_box(
    ocr_asset_path: str,
    bounding_box: tuple[int, int, int, int],
    expected_text: str,
    image_width: int,
    image_height: int,
):
    ocr_result = get_ocr_result_asset(ocr_asset_path)
    text = get_text_from_bounding_box(
        ocr_result, bounding_box, image_width, image_height
    )
    assert text == expected_text


def test_add_ingredient_in_taxonomy_field():
    parsed_ingredients = [
        {
            "id": "en:water",
            "text": "water",
            "percent_min": 33.3333333333333,
            "percent_max": 100,
            "percent_estimate": 66.6666666666667,
            "vegan": "yes",
            "vegetarian": "yes",
        },
        {
            "id": "en:salt",
            "text": "salt",
            "percent_min": 0,
            "percent_max": 50,
            "percent_estimate": 16.6666666666667,
            "vegan": "yes",
            "vegetarian": "yes",
        },
        {
            "id": "en:sugar",
            "text": "sugar",
            "percent_min": 0,
            "percent_max": 33.3333333333333,
            "percent_estimate": 16.6666666666667,
            "vegan": "yes",
            "vegetarian": "yes",
            "ingredients": [
                {
                    "id": "en:glucose",
                    "text": "glucose",
                    "percent_min": 0,
                    "percent_max": 100,
                    "percent_estimate": 100,
                    "vegan": "yes",
                    "vegetarian": "yes",
                },
                {
                    "id": "en:unknown-ingredient",
                    "text": "Unknown ingredient",
                    "percent_min": 0,
                    "percent_max": 100,
                    "percent_estimate": 100,
                },
            ],
        },
    ]
    ingredient_taxonomy = get_taxonomy(TaxonomyType.ingredient, offline=True)

    total_ingredients_n, known_ingredients_n = add_ingredient_in_taxonomy_field(
        parsed_ingredients, ingredient_taxonomy
    )

    assert total_ingredients_n == 5
    assert known_ingredients_n == 4

    assert parsed_ingredients == [
        {
            "id": "en:water",
            "text": "water",
            "percent_min": 33.3333333333333,
            "percent_max": 100,
            "percent_estimate": 66.6666666666667,
            "vegan": "yes",
            "vegetarian": "yes",
            "in_taxonomy": True,
        },
        {
            "id": "en:salt",
            "text": "salt",
            "percent_min": 0,
            "percent_max": 50,
            "percent_estimate": 16.6666666666667,
            "vegan": "yes",
            "vegetarian": "yes",
            "in_taxonomy": True,
        },
        {
            "id": "en:sugar",
            "text": "sugar",
            "percent_min": 0,
            "percent_max": 33.3333333333333,
            "percent_estimate": 16.6666666666667,
            "vegan": "yes",
            "vegetarian": "yes",
            "in_taxonomy": True,
            "ingredients": [
                {
                    "id": "en:glucose",
                    "text": "glucose",
                    "percent_min": 0,
                    "percent_max": 100,
                    "percent_estimate": 100,
                    "vegan": "yes",
                    "vegetarian": "yes",
                    "in_taxonomy": True,
                },
                {
                    "id": "en:unknown-ingredient",
                    "text": "Unknown ingredient",
                    "percent_min": 0,
                    "percent_max": 100,
                    "percent_estimate": 100,
                    "in_taxonomy": False,
                },
            ],
        },
    ]
