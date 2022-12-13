import datetime
import uuid
from typing import Optional

from robotoff import settings
from robotoff.insights.dataclass import InsightType
from robotoff.models import Prediction, ProductInsight, with_db
from robotoff.off import get_server_type
from robotoff.products import (
    DBProductStore,
    get_image_id,
    get_product_store,
    has_nutrition_image,
    is_nutrition_image,
    is_valid_image,
)
from robotoff.types import PredictionType
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)

FIBER_QUALITY_FACET_NAME = "en:missing-nutrition-facts-fibers-present-on-photos"
FIBER_NUTRITION_QUALITY_FACET_NAME = (
    "en:missing-nutrition-facts-fibers-present-on-nutrition-photos"
)


def generate_quality_facets():
    generate_fiber_quality_facet()


@with_db
def generate_fiber_quality_facet():
    product_store: DBProductStore = get_product_store()
    collection = product_store.collection
    added = 0
    seen_set: set[str] = set()

    for prediction in (
        Prediction.select(Prediction.barcode, Prediction.source_image)
        .where(
            Prediction.type == PredictionType.nutrient_mention.name,
            Prediction.data["mentions"].contains("fiber"),
            Prediction.source_image.is_null(False),
        )
        .iterator()
    ):
        barcode = prediction.barcode

        if barcode in seen_set:
            continue

        product = product_store.get_product(
            barcode, ["nutriments", "data_quality_tags", "images"]
        )

        if product is None:
            continue

        nutriments = product.get("nutriments", {})
        data_quality_tags = product.get("data_quality_tags", {})
        images = product.get("images", {})

        if (
            not is_valid_image(images, prediction.source_image)
            or "fiber" in nutriments
            or "fiber_prepared" in nutriments
        ):
            continue

        facets = []

        if FIBER_QUALITY_FACET_NAME not in data_quality_tags:
            facets.append(FIBER_QUALITY_FACET_NAME)

        if (
            FIBER_NUTRITION_QUALITY_FACET_NAME not in data_quality_tags
            and is_nutrition_image(images, prediction.source_image)
        ):
            facets.append(FIBER_NUTRITION_QUALITY_FACET_NAME)

        if not facets:
            continue

        logger.info("Adding facets to {}: {}".format(barcode, facets))
        seen_set.add(barcode)
        added += 1
        collection.update_one(
            {"code": barcode},
            {
                "$push": {
                    "data_quality_tags": {"$each": facets},
                    "data_quality_warnings_tags": {"$each": facets},
                }
            },
        )
    logger.info("Fiber quality facets added on {} products".format(added))


def get_image_orientation(barcode: str, image_id: str) -> Optional[int]:
    for prediction in (
        Prediction.select(Prediction.data, Prediction.source_image)
        .where(
            Prediction.barcode == barcode,
            Prediction.type == PredictionType.image_orientation.name,
            Prediction.server_domain == settings.OFF_SERVER_DOMAIN,
            Prediction.source_image.is_null(False),
        )
        .iterator()
    ):
        prediction_image_id = get_image_id(prediction.source_image)  # type: ignore

        if image_id is not None and prediction_image_id == image_id:
            return prediction.data.get("rotation")

    return None


def generate_nutrition_image_insights():
    logger.info("Starting nutrition image insight generation")
    logger.info("Deleting previous nutrition image insights...")
    deleted = (
        ProductInsight.delete()
        .where(
            ProductInsight.annotation.is_null(),
            ProductInsight.type == InsightType.nutrition_image.name,
            ProductInsight.server_domain == settings.OFF_SERVER_DOMAIN,
        )
        .execute()
    )
    logger.info("{} insights deleted".format(deleted))
    product_store: DBProductStore = get_product_store()
    added = 0
    seen_set: set[str] = set()

    prediction: Prediction
    for prediction in (
        Prediction.select()
        .where(Prediction.type == PredictionType.nutrient_mention.name)
        .order_by(Prediction.source_image.desc())
        .iterator()
    ):
        barcode = prediction.barcode

        if barcode in seen_set:
            continue

        mentions = prediction.data["mentions"]
        nutrition_image_langs = find_nutrition_image_lang(mentions)

        if not nutrition_image_langs:
            continue

        image_id = get_image_id(prediction.source_image)
        rotation = get_image_orientation(barcode, image_id)

        if rotation is None:
            continue

        product = product_store.get_product(barcode, ["images"])

        if product is None:
            continue

        images = product.get("images", {})

        if not has_nutrition_image(images):
            for lang in nutrition_image_langs:
                if not (
                    Prediction.select()
                    .where(
                        Prediction.type == PredictionType.nutrition_image.name,
                        Prediction.barcode == barcode,
                        Prediction.value_tag == lang,
                        Prediction.server_domain == settings.OFF_SERVER_DOMAIN,
                    )
                    .count()
                ):
                    ProductInsight.create(
                        id=str(uuid.uuid4()),
                        barcode=prediction.barcode,
                        type=InsightType.nutrition_image.name,
                        value_tag=lang,
                        timestamp=datetime.datetime.utcnow(),
                        source_image=prediction.source_image,
                        server_domain=prediction.server_domain,
                        server_type=get_server_type(prediction.server_domain).name,
                        automatic_processing=False,
                        data={
                            "from_prediction": str(prediction.id),
                            "languages": nutrition_image_langs,
                            "rotation": rotation or None,
                        },
                    )
                    added += 1

    logger.info("Added: {}".format(added))


def find_nutrition_image_lang(mentions: JSONType, min_count: int = 4) -> list[str]:
    nutrient_languages = find_nutrition_image_nutrient_languages(mentions)

    lang_count: dict[str, int] = {}
    for _, langs in nutrient_languages.items():
        for lang, count in langs.items():
            lang_count.setdefault(lang, 0)
            lang_count[lang] += count

    return [lang for lang, count in lang_count.items() if count >= min_count]


def find_nutrition_image_nutrient_languages(
    mentions: JSONType,
) -> dict[str, dict[str, int]]:
    languages: dict[str, dict[str, int]] = {}
    for nutrient, matches in mentions.items():
        seen_lang: set[str] = set()

        for match in matches:
            for lang in match.get("languages", []):
                if lang not in seen_lang:
                    languages.setdefault(nutrient, {})
                    nutrient_languages = languages[nutrient]
                    nutrient_languages.setdefault(lang, 0)
                    nutrient_languages[lang] += 1
                    seen_lang.add(lang)

    return languages
