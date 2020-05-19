import datetime
import pathlib
from typing import Optional

from robotoff.insights._enum import InsightType
from robotoff.insights.importer import InsightImporterFactory, BaseInsightImporter
from robotoff.insights.extraction import (
    get_insights_from_image,
    get_source_from_image_url,
)
from robotoff.models import db, ImageModel
from robotoff.off import get_server_type
from robotoff.products import (
    get_product_store,
    Product,
)
from robotoff.slack import notify_image_flag
from robotoff.utils import get_logger

logger = get_logger(__name__)


def import_image(barcode: str, image_url: str, ocr_url: str, server_domain: str):
    logger.info(
        "Detect insights for product {}, " "image {}".format(barcode, image_url)
    )
    product_store = get_product_store()
    product = product_store[barcode]
    save_image(barcode, image_url, product, server_domain)
    insights_all = get_insights_from_image(barcode, image_url, ocr_url)

    for insight_type, insights in insights_all.items():
        if insight_type == InsightType.image_flag:
            notify_image_flag(
                insights.insights,
                insights.source_image,  # type: ignore
                insights.barcode,
            )
            continue

        logger.info("Extracting {}".format(insight_type.name))
        importer: BaseInsightImporter = InsightImporterFactory.create(
            insight_type, product_store
        )

        with db.atomic():
            imported = importer.import_insights(
                [insights], server_domain=server_domain, automatic=True
            )
            logger.info("Import finished, {} insights imported".format(imported))


def save_image(
    barcode: str, image_url: str, product: Optional[Product], server_domain: str
) -> Optional[ImageModel]:
    """Save imported image details in DB."""
    if product is None:
        logger.warning(
            "Product {} does not exist during image import ({})".format(
                barcode, image_url
            )
        )
        return None

    source_image = get_source_from_image_url(image_url)
    image_id = pathlib.Path(source_image).stem

    if not image_id.isdigit():
        logger.warning("Non raw image was sent: {}".format(image_url))
        return None

    if image_id not in product.images:
        logger.warning("Unknown image for product {}: {}".format(barcode, image_url))
        return None

    image = product.images[image_id]
    sizes = image.get("sizes", {}).get("full")

    if not sizes:
        logger.warning("Image with missing size information: {}".format(image))
        return None

    width = sizes["w"]
    height = sizes["h"]

    if "uploaded_t" not in image:
        logger.warning("Missing uploaded_t field: {}".format(image.keys()))
        return None

    uploaded_at = datetime.datetime.utcfromtimestamp(image["uploaded_t"])
    return ImageModel.create(
        barcode=barcode,
        image_id=image_id,
        width=width,
        height=height,
        source_image=source_image,
        uploaded_at=uploaded_at,
        server_domain=server_domain,
        server_type=get_server_type(server_domain).name,
    )
