from robotoff.insights._enum import InsightType
from robotoff.models import LatentProductInsight
from robotoff.products import get_product_store, DBProductStore
from robotoff.utils import get_logger

logger = get_logger(__name__)

FIBER_QUALITY_FACET_NAME = "en:missing-nutrition-facts-fibers-present-on-photos"


def generate_insights_from_latent_insights():
    generate_fiber_quality_facet()


def generate_fiber_quality_facet():
    product_store: DBProductStore = get_product_store()
    collection = product_store.collection

    for latent_insight in LatentProductInsight.select(
        LatentProductInsight.barcode
    ).where(
        LatentProductInsight.type == InsightType.nutrient_mention.name,
        LatentProductInsight.data["mentions"].contains("fiber"),
    ):
        barcode = latent_insight.barcode
        product = product_store.get_product(barcode, ["fiber"])

        if product is None or "fiber" in product:
            continue

        logger.info("Adding {} facet to {}".format(FIBER_QUALITY_FACET_NAME, barcode))
        collection.update_one(
            {"code": barcode},
            {
                "$push": {
                    "data_quality_tags": FIBER_QUALITY_FACET_NAME,
                    "data_quality_warnings_tags": FIBER_QUALITY_FACET_NAME,
                }
            },
        )
