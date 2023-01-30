import abc
import pathlib
from typing import Optional

from robotoff import settings
from robotoff.models import ProductInsight
from robotoff.mongo import MONGO_CLIENT_CACHE
from robotoff.off import generate_image_url
from robotoff.products import get_product
from robotoff.taxonomy import Taxonomy, TaxonomyType, get_taxonomy
from robotoff.types import InsightType, JSONType
from robotoff.utils import get_logger, load_json
from robotoff.utils.i18n import TranslationStore

logger = get_logger(__name__)

DISPLAY_IMAGE_SIZE = 400
SMALL_IMAGE_SIZE = 200
THUMB_IMAGE_SIZE = 100


LABEL_IMAGES: dict[str, str] = load_json(settings.LABEL_LOGOS_PATH)  # type: ignore


def generate_selected_images(
    images: JSONType, barcode: str
) -> dict[str, dict[str, dict[str, str]]]:
    """Generate the same `selected_images` field as returned by Product
    Opener API.

    :param images: the `images` data of the product
    :param barcode: the product barcode
    :return: the `selected_images` data
    """
    selected_images: dict[str, dict[str, dict[str, str]]] = {
        image_type: {}
        for image_type in ("front", "nutrition", "ingredients", "packaging")
    }

    for key, image_data in images.items():
        if (
            key.startswith("front_")
            or key.startswith("nutrition_")
            or key.startswith("ingredients_")
            or key.startswith("packaging_")
        ):
            image_type = key.split("_")[
                0
            ]  # to get image type: `front`, `nutrition`, `ingredients` or `packaging`
            language = key.split("_")[1]  # splitting to get the language name
            revision_id = image_data["rev"]  # get revision_id for all languages
            available_image_sizes = set(
                int(size) for size in image_data["sizes"] if size.isdigit()
            )

            for field_name, image_size in (
                ("display", DISPLAY_IMAGE_SIZE),
                ("small", SMALL_IMAGE_SIZE),
                ("thumb", THUMB_IMAGE_SIZE),
            ):
                if image_size in available_image_sizes:
                    image_url = generate_image_url(
                        barcode, f"{key}.{revision_id}.{image_size}"
                    )
                    selected_images[image_type].setdefault(field_name, {})
                    selected_images[image_type][field_name][language] = image_url

    return selected_images


def get_source_image_url(
    barcode: str, field_types: Optional[list[str]] = None
) -> Optional[str]:
    """Generate the URL of a generic image to display for an insight.

    By default, we check in order that the product has an image in any
    language of the following types ("front", "ingredients", "nutrition"),
    and use this image to generate the image URL.

    :param barcode: the barcode of the product
    :param field_types: the image field types to check. If not provided,
      we use ["front", "ingredients", "nutrition"]
    :return: The image URL or None if no suitable image has been found
    """
    if field_types is None:
        field_types = ["front", "ingredients", "nutrition"]

    product: Optional[JSONType] = get_product(barcode, ["images"])

    if product is None or "images" not in product:
        return None

    selected_images = generate_selected_images(product["images"], barcode)

    for key in field_types:
        if key in selected_images:
            images = selected_images[key]

            if "display" in images:
                display_images = list(images["display"].values())

                if display_images:
                    return display_images[0]

    return None


class Question(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def serialize(self) -> JSONType:
        pass

    @abc.abstractmethod
    def get_type(self):
        pass


class AddBinaryQuestion(Question):
    """JSON formatter for a binary (yes/no) question.

    :param question: The non-localized question text (in English)
    :param value: the suggested answer to the question
    :param insight: the insight used to generate the question
    :param ref_image_url: the URL of a reference image, used to display the
    image of the logo for `label` insights, optional
    :param source_image_url: the URL of the image from where the insight was
    extracted from, optional
    :param value_tag: The `value_tag` that is going to be sent to Product
    Opener if the insight is validated, optional
    """

    def __init__(
        self,
        question: str,
        value: str,
        insight: ProductInsight,
        ref_image_url: Optional[str] = None,
        source_image_url: Optional[str] = None,
        value_tag: Optional[str] = None,
    ):
        self.question: str = question
        self.value: str = value
        self.insight_id: str = str(insight.id)
        self.insight_type: str = str(insight.type)
        self.barcode: str = insight.barcode
        self.ref_image_url: Optional[str] = ref_image_url
        self.source_image_url: Optional[str] = source_image_url
        self.value_tag: Optional[str] = value_tag

    def get_type(self):
        return "add-binary"

    def serialize(self) -> JSONType:
        serial = {
            "barcode": self.barcode,
            "type": self.get_type(),
            "value": self.value,
            "question": self.question,
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
        }

        if self.value_tag:
            serial["value_tag"] = self.value_tag

        if self.ref_image_url:
            serial["ref_image_url"] = self.ref_image_url

        if self.source_image_url:
            serial["source_image_url"] = self.source_image_url

        return serial


class IngredientSpellcheckQuestion(Question):
    def __init__(self, insight: ProductInsight, ref_image_url: Optional[str]):
        self.insight_id: str = str(insight.id)
        self.insight_type: str = str(insight.type)
        self.barcode: str = insight.barcode
        self.corrected: str = insight.data["corrected"]
        self.text: str = insight.data["text"]
        self.corrections: list[JSONType] = insight.data["corrections"]
        self.lang: str = insight.data["lang"]
        self.ref_image_url: Optional[str] = ref_image_url

    def get_type(self):
        return "ingredient-spellcheck"

    def serialize(self) -> JSONType:
        serial = {
            "barcode": self.barcode,
            "type": self.get_type(),
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "text": self.text,
            "corrected": self.corrected,
            "corrections": self.corrections,
            "lang": self.lang,
        }

        if self.ref_image_url:
            serial["ref_image_url"] = self.ref_image_url

        return serial


class QuestionFormatter(metaclass=abc.ABCMeta):
    def __init__(self, translation_store: TranslationStore):
        self.translation_store: TranslationStore = translation_store

    @abc.abstractmethod
    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        pass


class CategoryQuestionFormatter(QuestionFormatter):
    question = "Does the product belong to this category?"

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        taxonomy: Taxonomy = get_taxonomy(TaxonomyType.category.name)
        localized_value: str = taxonomy.get_localized_name(insight.value_tag, lang)
        localized_question = self.translation_store.gettext(lang, self.question)
        source_image_url = get_source_image_url(insight.barcode)
        return AddBinaryQuestion(
            question=localized_question,
            value=localized_value,
            value_tag=insight.value_tag,
            insight=insight,
            source_image_url=source_image_url,
        )

    @staticmethod
    def generate_selected_images(
        images: JSONType, barcode: str
    ) -> dict[str, dict[str, dict[str, str]]]:
        """Generate the same `selected_images` field as returned by Product
        Opener API.

        :param images: the `images` data of the product
        :param barcode: the product barcode
        :return: the `selected_images` data
        """
        selected_images: dict[str, dict[str, dict[str, str]]] = {
            image_type: {}
            for image_type in ("front", "nutrition", "ingredients", "packaging")
        }

        for key, image_data in images.items():
            if (
                key.startswith("front_")
                or key.startswith("nutrition_")
                or key.startswith("ingredients_")
                or key.startswith("packaging_")
            ):
                image_type = key.split("_")[
                    0
                ]  # to get image type: `front`, `nutrition`, `ingredients` or `packaging`
                language = key.split("_")[1]  # splitting to get the language name
                revision_id = image_data["rev"]  # get revision_id for all languages
                available_image_sizes = set(
                    int(size) for size in image_data["sizes"] if size.isdigit()
                )

                for field_name, image_size in (
                    ("display", DISPLAY_IMAGE_SIZE),
                    ("small", SMALL_IMAGE_SIZE),
                    ("thumb", THUMB_IMAGE_SIZE),
                ):
                    if image_size in available_image_sizes:
                        image_url = generate_image_url(
                            barcode, f"{key}.{revision_id}.{image_size}"
                        )
                        selected_images[image_type].setdefault(field_name, {})
                        selected_images[image_type][field_name][language] = image_url

        return selected_images


class ProductWeightQuestionFormatter(QuestionFormatter):
    question = "Does this weight match the weight displayed on the product?"

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.source_image:
            source_image_url = settings.BaseURLProvider.image_url(
                get_display_image(insight.source_image)
            )

        return AddBinaryQuestion(
            question=localized_question,
            value=insight.value,
            insight=insight,
            source_image_url=source_image_url,
        )


class LabelQuestionFormatter(QuestionFormatter):
    question = "Does the product have this label?"

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        value_tag: str = insight.value_tag
        ref_image_url = LABEL_IMAGES.get(value_tag)

        taxonomy: Taxonomy = get_taxonomy(TaxonomyType.label.name)
        localized_value: str = taxonomy.get_localized_name(value_tag, lang)
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.source_image:
            source_image_url = settings.BaseURLProvider.image_url(
                get_display_image(insight.source_image)
            )

        return AddBinaryQuestion(
            question=localized_question,
            value=localized_value,
            value_tag=value_tag,
            insight=insight,
            ref_image_url=ref_image_url,
            source_image_url=source_image_url,
        )


class PackagingQuestionFormatter(QuestionFormatter):
    question = "Does the product have this packaging element?"
    packaging_taxonomy_types = {
        "shape": TaxonomyType.packaging_shape,
        "material": TaxonomyType.packaging_material,
        "recycling": TaxonomyType.packaging_recycling,
    }

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        element = insight.data["element"]
        taxonomies: dict[TaxonomyType, Taxonomy] = {
            taxonomy_type: get_taxonomy(taxonomy_type.name)
            for taxonomy_type in self.packaging_taxonomy_types.values()
        }

        localized_value_list = []
        for element_property, taxonomy_type in self.packaging_taxonomy_types.items():
            value = element.get(element_property, {}).get("value_tag")
            if value:
                localized_value_list.append(
                    taxonomies[taxonomy_type].get_localized_name(value, lang)
                )
        localized_value = ", ".join(localized_value_list)
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.source_image:
            source_image_url = settings.BaseURLProvider.image_url(
                get_display_image(insight.source_image)
            )

        return AddBinaryQuestion(
            question=localized_question,
            value=localized_value,
            insight=insight,
            source_image_url=source_image_url,
        )


class BrandQuestionFormatter(QuestionFormatter):
    question = "Does the product belong to this brand?"

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.predictor in ("curated-list", "taxonomy", "whitelisted-brands"):
            # Use front image as default for flashtext-brand insights
            source_image_url = get_source_image_url(
                insight.barcode, field_types=["front"]
            )

        if source_image_url is None and insight.source_image:
            source_image_url = settings.BaseURLProvider.image_url(
                get_display_image(insight.source_image)
            )

        return AddBinaryQuestion(
            question=localized_question,
            value=insight.value,
            value_tag=insight.value_tag,
            insight=insight,
            source_image_url=source_image_url,
        )


class IngredientSpellcheckQuestionFormatter(QuestionFormatter):
    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        ref_image_url = self.get_ingredient_image_url(insight.barcode, lang)
        return IngredientSpellcheckQuestion(
            insight=insight, ref_image_url=ref_image_url
        )

    def get_ingredient_image_url(self, barcode: str, lang: str) -> Optional[str]:
        mongo_client = MONGO_CLIENT_CACHE.get()
        collection = mongo_client.off.products
        product = collection.find_one({"code": barcode}, ["images"])

        if product is None:
            return None

        images = product.get("images", {})
        field_name = "ingredients_{}".format(lang)

        if field_name in images:
            image = images[field_name]
            image_id = "ingredients_{}.{}.full".format(lang, image["rev"])
            return generate_image_url(barcode, image_id)

        return None


class NutritionImageQuestionFormatter(QuestionFormatter):
    question = "Is this image a nutrition image for this language?"

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.source_image:
            source_image_url = settings.BaseURLProvider.image_url(
                get_display_image(insight.source_image)
            )

        return AddBinaryQuestion(
            question=localized_question,
            value=insight.value_tag,
            insight=insight,
            source_image_url=source_image_url,
        )


def get_display_image(source_image: str) -> str:
    image_path = pathlib.Path(source_image)

    if not image_path.stem.isdigit():
        return source_image

    display_name = "{}.400.jpg".format(image_path.name.split(".")[0])
    return str(image_path.parent / display_name)


class QuestionFormatterFactory:
    formatters: dict[str, type] = {
        InsightType.category.name: CategoryQuestionFormatter,
        InsightType.label.name: LabelQuestionFormatter,
        InsightType.product_weight.name: ProductWeightQuestionFormatter,
        InsightType.brand.name: BrandQuestionFormatter,
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckQuestionFormatter,
        InsightType.nutrition_image.name: NutritionImageQuestionFormatter,
        InsightType.packaging.name: PackagingQuestionFormatter,
    }

    @classmethod
    def get(cls, insight_type: str):
        return cls.formatters.get(insight_type)

    @classmethod
    def get_available_types(cls) -> list[str]:
        return list(cls.formatters.keys())

    @classmethod
    def get_default_types(cls) -> list[str]:
        return [
            InsightType.category.name,
            InsightType.label.name,
            InsightType.product_weight.name,
            InsightType.brand.name,
            InsightType.packaging.name,
        ]
