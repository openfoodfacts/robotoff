import abc
import pathlib
from typing import Dict, List, Optional

from robotoff import settings
from robotoff.insights import InsightType
from robotoff.models import ProductInsight
from robotoff.mongo import MONGO_CLIENT_CACHE
from robotoff.off import generate_image_url, split_barcode
from robotoff.products import get_product
from robotoff.taxonomy import Taxonomy, TaxonomyType, get_taxonomy
from robotoff.utils import get_logger
from robotoff.utils.i18n import TranslationStore
from robotoff.utils.types import JSONType

logger = get_logger(__name__)

IMAGE_SUB_DOMAIN = "https://images.openfoodfacts.org"

DISPLAY_IMAGE_SIZE = 400
SMALL_IMAGE_SIZE = 200
THUMB_IMAGE_SIZE = 100


LABEL_IMG_BASE_URL = "https://{}/images/lang".format(
    settings.BaseURLProvider().static().get()
)

LABEL_IMAGES = {
    "en:eu-organic": LABEL_IMG_BASE_URL + "/en/labels/eu-organic.135x90.svg",
    "en:ab-agriculture-biologique": LABEL_IMG_BASE_URL
    + "/fr/labels/ab-agriculture-biologique.74x90.svg",
    "en:european-vegetarian-union": LABEL_IMG_BASE_URL
    + "/en/labels/european-vegetarian-union.90x90.svg",
    "en:pgi": LABEL_IMG_BASE_URL + "/en/labels/pgi.90x90.png",
}


class Question(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def serialize(self) -> JSONType:
        pass

    @abc.abstractmethod
    def get_type(self):
        pass


class AddBinaryQuestion(Question):
    def __init__(
        self,
        question: str,
        value: str,
        insight: ProductInsight,
        image_url: Optional[str] = None,
        source_image_url: Optional[str] = None,
        value_tag: Optional[str] = None,
    ):
        self.question: str = question
        self.value: str = value
        self.insight_id: str = str(insight.id)
        self.insight_type: str = str(insight.type)
        self.barcode: str = insight.barcode
        self.image_url: Optional[str] = image_url
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

        if self.image_url:
            serial["image_url"] = self.image_url

        if self.source_image_url:
            serial["source_image_url"] = self.source_image_url

        return serial


class IngredientSpellcheckQuestion(Question):
    def __init__(self, insight: ProductInsight, image_url: Optional[str]):
        self.insight_id: str = str(insight.id)
        self.insight_type: str = str(insight.type)
        self.barcode: str = insight.barcode
        self.corrected: str = insight.data["corrected"]
        self.text: str = insight.data["text"]
        self.corrections: List[JSONType] = insight.data["corrections"]
        self.lang: str = insight.data["lang"]
        self.image_url: Optional[str] = image_url

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

        if self.image_url:
            serial["image_url"] = self.image_url

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
        source_image_url = self.get_source_image_url(insight.barcode)
        return AddBinaryQuestion(
            question=localized_question,
            value=localized_value,
            value_tag=insight.value_tag,
            insight=insight,
            source_image_url=source_image_url,
        )

    @staticmethod
    def get_source_image_url(barcode: str) -> Optional[str]:
        product: Optional[JSONType] = get_product(barcode)

        if product is None:
            return None

        selected_images = CategoryQuestionFormatter.generate_selected_images(
            product, barcode
        )

        for key in ("front", "ingredients", "nutrition"):
            if key in selected_images:
                images = selected_images[key]

                if "display" in images:
                    display_images = list(images["display"].values())

                    if display_images:
                        return display_images[0]

        return None

    @staticmethod
    def generate_selected_images(images: JSONType, barcode: str) -> JSONType:
        selected_images: Dict[str, Dict[str, Dict[str, str]]] = {
            "front": {"display": {}, "small": {}, "thumb": {}},
            "nutrition": {"display": {}, "small": {}, "thumb": {}},
            "ingredients": {"display": {}, "small": {}, "thumb": {}},
            "packaging": {"display": {}, "small": {}, "thumb": {}},
        }
        splitted_barcode = split_barcode(barcode)  # splitting the barcode
        image_url = "{}/images/products/{}/{}.{}.{}.jpg"

        for key, images in images.items():
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
                revision_id = images["rev"]  # get revision_id for all languages

                selected_images[image_type]["display"].update(
                    {
                        language: image_url.format(
                            IMAGE_SUB_DOMAIN,
                            "/".join(splitted_barcode),
                            key,
                            revision_id,
                            DISPLAY_IMAGE_SIZE,
                        )
                    }
                )
                selected_images[image_type]["small"].update(
                    {
                        language: image_url.format(
                            IMAGE_SUB_DOMAIN,
                            "/".join(splitted_barcode),
                            key,
                            revision_id,
                            SMALL_IMAGE_SIZE,
                        )
                    }
                )

                selected_images[image_type]["thumb"].update(
                    {
                        language: image_url.format(
                            IMAGE_SUB_DOMAIN,
                            "/".join(splitted_barcode),
                            key,
                            revision_id,
                            THUMB_IMAGE_SIZE,
                        )
                    }
                )

        return selected_images


class ProductWeightQuestionFormatter(QuestionFormatter):
    question = "Does this weight match the weight displayed on the product?"

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.source_image:
            source_image_url = settings.OFF_IMAGE_BASE_URL + get_display_image(
                insight.source_image
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
        image_url = None

        if value_tag in LABEL_IMAGES:
            image_url = LABEL_IMAGES[value_tag]

        taxonomy: Taxonomy = get_taxonomy(TaxonomyType.label.name)
        localized_value: str = taxonomy.get_localized_name(value_tag, lang)
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.source_image:
            source_image_url = settings.OFF_IMAGE_BASE_URL + get_display_image(
                insight.source_image
            )

        return AddBinaryQuestion(
            question=localized_question,
            value=localized_value,
            value_tag=value_tag,
            insight=insight,
            image_url=image_url,
            source_image_url=source_image_url,
        )


class BrandQuestionFormatter(QuestionFormatter):
    question = "Does the product belong to this brand?"

    def format_question(self, insight: ProductInsight, lang: str) -> Question:
        localized_question = self.translation_store.gettext(lang, self.question)

        source_image_url = None
        if insight.source_image:
            source_image_url = settings.OFF_IMAGE_BASE_URL + get_display_image(
                insight.source_image
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
        image_url = self.get_ingredient_image_url(insight.barcode, lang)
        return IngredientSpellcheckQuestion(insight=insight, image_url=image_url)

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
            source_image_url = settings.OFF_IMAGE_BASE_URL + get_display_image(
                insight.source_image
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
    formatters: Dict[str, type] = {
        InsightType.category.name: CategoryQuestionFormatter,
        InsightType.label.name: LabelQuestionFormatter,
        InsightType.product_weight.name: ProductWeightQuestionFormatter,
        InsightType.brand.name: BrandQuestionFormatter,
        InsightType.ingredient_spellcheck.name: IngredientSpellcheckQuestionFormatter,
        InsightType.nutrition_image.name: NutritionImageQuestionFormatter,
    }

    @classmethod
    def get(cls, insight_type: str):
        return cls.formatters.get(insight_type)

    @classmethod
    def get_available_types(cls) -> List[str]:
        return list(cls.formatters.keys())

    @classmethod
    def get_default_types(cls) -> List[str]:
        return [
            InsightType.category.name,
            InsightType.label.name,
            InsightType.product_weight.name,
            InsightType.brand.name,
        ]
