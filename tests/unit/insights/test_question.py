import json

import pytest

from robotoff.insights.question import CategoryQuestionFormatter, get_display_image
from robotoff.settings import TEST_DATA_DIR

with (TEST_DATA_DIR / "generate_images.json").open("r") as f:
    IMAGE_DATA = json.load(f)


@pytest.mark.parametrize(
    "source_image,output",
    [
        ("/366/194/903/0038/1.jpg", "/366/194/903/0038/1.400.jpg"),
        ("/366/194/903/0038/20.jpg", "/366/194/903/0038/20.400.jpg"),
        ("/366/194/903/0038/20.400.jpg", "/366/194/903/0038/20.400.jpg"),
        ("/366/194/903/0038/20test.jpg", "/366/194/903/0038/20test.jpg"),
    ],
)
def test_get_display_image(source_image: str, output: str):
    assert get_display_image(source_image) == output


def test_generate_selected_images():
    selected_images = CategoryQuestionFormatter.generate_selected_images(
        IMAGE_DATA["product"]["images"], IMAGE_DATA["code"]
    )

    assert selected_images["front"] == {
        "display": {
            "es": "https://static.openfoodfacts.net/images/products/541/004/104/0807/front_es.130.400.jpg",
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/front_fr.142.400.jpg",
        },
        "small": {
            "es": "https://static.openfoodfacts.net/images/products/541/004/104/0807/front_es.130.200.jpg",
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/front_fr.142.200.jpg",
        },
        "thumb": {
            "es": "https://static.openfoodfacts.net/images/products/541/004/104/0807/front_es.130.100.jpg",
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/front_fr.142.100.jpg",
        },
    }

    assert selected_images["nutrition"] == {
        "display": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/nutrition_fr.145.400.jpg"
        },
        "small": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/nutrition_fr.145.200.jpg"
        },
        "thumb": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/nutrition_fr.145.100.jpg"
        },
    }

    assert selected_images["ingredients"] == {
        "display": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/ingredients_fr.144.400.jpg"
        },
        "small": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/ingredients_fr.144.200.jpg"
        },
        "thumb": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/ingredients_fr.144.100.jpg"
        },
    }

    assert selected_images["packaging"] == {
        "display": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/packaging_fr.146.400.jpg"
        },
        "small": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/packaging_fr.146.200.jpg"
        },
        "thumb": {
            "fr": "https://static.openfoodfacts.net/images/products/541/004/104/0807/packaging_fr.146.100.jpg"
        },
    }
