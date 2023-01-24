from robotoff.models import Prediction, with_db
from robotoff.products import (
    DBProductStore,
    get_product_store,
    is_nutrition_image,
    is_valid_image,
)
from robotoff.types import PredictionType
from robotoff.utils import get_logger

logger = get_logger(__name__)

FIBER_QUALITY_FACET_NAME = "en:missing-nutrition-facts-fibers-present-on-photos"
FIBER_NUTRITION_QUALITY_FACET_NAME = (
    "en:missing-nutrition-facts-fibers-present-on-nutrition-photos"
)


def generate_quality_facets():
    generate_fiber_quality_facet()


@with_db
def generate_fiber_quality_facet() -> None:
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

        logger.info("Adding facets to %s: %s", (barcode, facets))
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
    logger.info("Fiber quality facets added on %s products", added)
