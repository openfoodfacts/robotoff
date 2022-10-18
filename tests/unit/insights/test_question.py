import json
from typing import Optional

import pytest

from robotoff.insights.dataclass import InsightType
from robotoff.insights.question import (
    CategoryQuestionFormatter,
    Question,
    get_display_image,
)
from robotoff.models import ProductInsight
from robotoff.off import split_barcode
from robotoff.settings import TEST_DATA_DIR
from robotoff.utils.i18n import TranslationStore


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
    with (TEST_DATA_DIR / "generate_selected_images.json").open("r") as f:
        IMAGE_DATA = json.load(f)

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


def generate_insight(
    insight_type: str,
    value: Optional[str] = None,
    value_tag: Optional[str] = None,
    add_source_image: bool = False,
) -> ProductInsight:
    barcode = "1111111111"
    return ProductInsight(
        type=insight_type,
        value=value,
        value_tag=value_tag,
        barcode=barcode,
        source_image=f"/{'/'.join(split_barcode(barcode))}/1.jpg"
        if add_source_image
        else None,
    )


@pytest.fixture(scope="session")
def translation_store():
    store = TranslationStore()
    store.load()
    return store


@pytest.mark.parametrize(
    "lang,insight_type,value,value_tag,expected_question_str",
    [
        (
            "fr",
            InsightType.category.name,
            "Pains",
            "en:breads",
            "Le produit appartient-il à cette catégorie ?",
        ),
        (
            "en",
            InsightType.category.name,
            "Butters",
            "en:butters",
            "Does the product belong to this category?",
        ),
        (
            "es",
            InsightType.category.name,
            "Mantequillas",
            "en:butters",
            "¿Pertenece el producto a esta categoría?",
        ),
    ],
)
def test_category_question_formatter(
    lang: str,
    insight_type: str,
    value: str,
    value_tag: Optional[str],
    expected_question_str: str,
    translation_store: TranslationStore,
    mocker,
):
    mocker.patch(
        "robotoff.insights.question.get_product",
        return_value={"images": {"front_fr": {"rev": "10", "sizes": {"400": {}}}}},
    )
    insight = generate_insight(insight_type, None, value_tag, add_source_image=False)
    question = CategoryQuestionFormatter(translation_store).format_question(
        insight, lang
    )
    assert isinstance(question, Question)
    assert question.serialize() == {
        "barcode": insight.barcode,
        "type": "add-binary",
        "value": value,
        "value_tag": value_tag,
        "question": expected_question_str,
        "insight_id": str(insight.id),
        "insight_type": insight_type,
        "source_image_url": "https://static.openfoodfacts.net/images/products/111/111/111/1/front_fr.10.400.jpg",
    }
