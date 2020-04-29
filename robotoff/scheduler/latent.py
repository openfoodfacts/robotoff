import pathlib

from robotoff.insights._enum import InsightType
from robotoff.models import LatentProductInsight
from robotoff.products import get_product_store, DBProductStore
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

logger = get_logger(__name__)

FIBER_QUALITY_FACET_NAME = "en:missing-nutrition-facts-fibers-present-on-photos"


def generate_quality_facets():
    generate_fiber_quality_facet()


def is_valid_image(images: JSONType, image_path: str) -> bool:
    image_id = pathlib.Path(image_path).stem
    if not image_id.isdigit():
        return False

    return image_id in images


def generate_fiber_quality_facet():
    product_store: DBProductStore = get_product_store()
    collection = product_store.collection
    added = 0

    for latent_insight in LatentProductInsight.select(
        LatentProductInsight.barcode, LatentProductInsight.source_image
    ).where(
        LatentProductInsight.type == InsightType.nutrient_mention.name,
        LatentProductInsight.data["mentions"].contains("fiber"),
        LatentProductInsight.source_image.is_null(False),
    ):
        barcode = latent_insight.barcode
        product = product_store.get_product(
            barcode, ["nutriments", "data_quality_tags", "images"]
        )
        if (
            product is None
            or not (product.get("images", {}), latent_insight.source_image)
            or "fiber" in product.get("nutriments", {})
            or FIBER_QUALITY_FACET_NAME in product.get("data_quality_tags", [])
        ):
            continue

        logger.info("Adding {} facet to {}".format(FIBER_QUALITY_FACET_NAME, barcode))
        added += 1
        collection.update_one(
            {"code": barcode},
            {
                "$push": {
                    "data_quality_tags": FIBER_QUALITY_FACET_NAME,
                    "data_quality_warnings_tags": FIBER_QUALITY_FACET_NAME,
                }
            },
        )
    logger.info(
        "Quality facet {} added on {} products".format(FIBER_QUALITY_FACET_NAME, added)
    )
