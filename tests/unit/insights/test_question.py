import json

import pytest
from openfoodfacts.images import split_barcode

from robotoff.insights.question import (
    CategoryQuestionFormatter,
    ImageOrientationQuestionFormatter,
    LabelQuestionFormatter,
    Question,
    generate_selected_images,
    get_display_image,
)
from robotoff.models import ProductInsight
from robotoff.settings import TEST_DATA_DIR
from robotoff.types import InsightType, JSONType, ProductIdentifier, ServerType
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

    selected_images = generate_selected_images(
        IMAGE_DATA["product"]["images"],
        ProductIdentifier(IMAGE_DATA["code"], ServerType.off),
    )

    assert selected_images["front"] == {
        "display": {
            "es": "https://images.openfoodfacts.net/images/products/541/004/104/0807/front_es.130.400.jpg",
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/front_fr.142.400.jpg",
        },
        "small": {
            "es": "https://images.openfoodfacts.net/images/products/541/004/104/0807/front_es.130.200.jpg",
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/front_fr.142.200.jpg",
        },
        "thumb": {
            "es": "https://images.openfoodfacts.net/images/products/541/004/104/0807/front_es.130.100.jpg",
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/front_fr.142.100.jpg",
        },
    }

    assert selected_images["nutrition"] == {
        "display": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/nutrition_fr.145.400.jpg"
        },
        "small": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/nutrition_fr.145.200.jpg"
        },
        "thumb": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/nutrition_fr.145.100.jpg"
        },
    }

    assert selected_images["ingredients"] == {
        "display": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/ingredients_fr.144.400.jpg"
        },
        "small": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/ingredients_fr.144.200.jpg"
        },
        "thumb": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/ingredients_fr.144.100.jpg"
        },
    }

    assert selected_images["packaging"] == {
        "display": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/packaging_fr.146.400.jpg"
        },
        "small": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/packaging_fr.146.200.jpg"
        },
        "thumb": {
            "fr": "https://images.openfoodfacts.net/images/products/541/004/104/0807/packaging_fr.146.100.jpg"
        },
    }


def generate_insight(
    insight_type: str,
    value: str | None = None,
    value_tag: str | None = None,
    add_source_image: bool = False,
    server_type: ServerType = ServerType.off,
    data: JSONType | None = None,
) -> ProductInsight:
    barcode = "1111111111"
    data = data or {}
    return ProductInsight(
        type=insight_type,
        value=value,
        value_tag=value_tag,
        barcode=barcode,
        source_image=(
            f"/{'/'.join(split_barcode(barcode))}/1.jpg" if add_source_image else None
        ),
        data=data,
        server_type=server_type.name,
    )


@pytest.fixture(scope="session")
def translation_store():
    store = TranslationStore()
    store.load()
    return store


@pytest.mark.parametrize(
    "lang,value,value_tag,expected_question_str",
    [
        (
            "fr",
            "Pains",
            "en:breads",
            "Le produit appartient-il à cette catégorie ?",
        ),
        (
            "en",
            "Butters",
            "en:butters",
            "Does the product belong to this category?",
        ),
        (
            "es",
            "Mantequillas",
            "en:butters",
            "¿Pertenece el producto a esta categoría?",
        ),
    ],
)
def test_category_question_formatter(
    lang: str,
    value: str,
    value_tag: str | None,
    expected_question_str: str,
    translation_store: TranslationStore,
    mocker,
):
    mocker.patch(
        "robotoff.insights.question.get_product",
        return_value={"images": {"front_fr": {"rev": "10", "sizes": {"400": {}}}}},
    )
    insight = generate_insight(
        InsightType.category.name, None, value_tag, add_source_image=False
    )
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
        "insight_type": InsightType.category.name,
        "server_type": ServerType.off.name,
        "source_image_url": "https://images.openfoodfacts.net/images/products/000/111/111/1111/front_fr.10.400.jpg",
    }


@pytest.mark.parametrize(
    "lang,value,value_tag,expected_question_str,ref_image_url",
    [
        (
            "fr",
            "Bio européen",
            "en:eu-organic",
            "Le produit a-t-il ce label ?",
            "https://static.openfoodfacts.org/images/lang/en/labels/eu-organic.135x90.svg",
        ),
        (
            "en",
            "Nutriscore Grade A",
            "en:nutriscore-grade-a",
            "Does the product have this label?",
            "https://static.openfoodfacts.org/images/attributes/dist/nutriscore-a.svg",
        ),
        (
            "en",
            "Made in France",
            "en:made-in-france",
            "Does the product have this label?",
            None,
        ),
    ],
)
def test_label_question_formatter(
    lang: str,
    value: str,
    value_tag: str,
    expected_question_str: str,
    ref_image_url: str | None,
    translation_store: TranslationStore,
):
    insight = generate_insight(
        InsightType.label.name, None, value_tag, add_source_image=True
    )
    question = LabelQuestionFormatter(translation_store).format_question(insight, lang)
    assert isinstance(question, Question)
    expected_dict = {
        "barcode": insight.barcode,
        "type": "add-binary",
        "value": value,
        "value_tag": value_tag,
        "question": expected_question_str,
        "insight_id": str(insight.id),
        "insight_type": InsightType.label.name,
        "server_type": ServerType.off.name,
        "source_image_url": "https://images.openfoodfacts.net/images/products/000/111/111/1111/1.400.jpg",
    }

    if ref_image_url is not None:
        expected_dict["ref_image_url"] = ref_image_url
    assert question.serialize() == expected_dict


class TestImageOrientationQuestionFormatter:
    def test_format_question(self, mocker, translation_store):
        insight = generate_insight(
            insight_type=InsightType.image_orientation.name,
            value_tag="right",
            add_source_image=True,
            server_type=ServerType.off,
            data={"image_key": "front_fr", "image_rev": "10"},
        )
        question = ImageOrientationQuestionFormatter(translation_store).format_question(
            insight, "en"
        )
        assert isinstance(question, Question)
        assert question.serialize() == {
            "barcode": insight.barcode,
            "type": "add-binary",
            "value": "right",
            "question": "Is this image rotated with the following orientation?",
            "insight_id": str(insight.id),
            "insight_type": InsightType.image_orientation.name,
            "server_type": ServerType.off.name,
            "source_image_url": "https://images.openfoodfacts.net/images/products/000/111/111/1111/front_fr.10.400.jpg",
        }
