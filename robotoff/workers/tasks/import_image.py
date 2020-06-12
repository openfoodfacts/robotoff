import datetime
import pathlib
from typing import Optional

from robotoff import settings
from robotoff.insights._enum import InsightType
from robotoff.insights.extraction import (
    get_insights_from_image,
    get_source_from_image_url,
    predict_objects,
)
from robotoff.insights.importer import BaseInsightImporter, InsightImporterFactory
from robotoff.logos import add_logos_to_ann, predict_logo_label, save_nearest_neighbors
from robotoff.models import db, ImageModel, ImagePrediction, LogoAnnotation
from robotoff.off import get_server_type
from robotoff.products import get_product_store, Product
from robotoff.slack import notify_image_flag
from robotoff.utils import get_logger
from robotoff.workers.client import send_ipc_event

logger = get_logger(__name__)


def import_image(barcode: str, image_url: str, ocr_url: str, server_domain: str):
    logger.info(
        "Detect insights for product {}, " "image {}".format(barcode, image_url)
    )
    product_store = get_product_store()
    product = product_store[barcode]
    save_image(barcode, image_url, product, server_domain)
    launch_object_detection_job(barcode, image_url, server_domain)
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

    uploaded_t = image["uploaded_t"]
    if isinstance(uploaded_t, str):
        if not uploaded_t.isdigit():
            logger.warning("Non digit uploaded_t value: {}".format(uploaded_t))
            return None

        uploaded_t = int(uploaded_t)

    uploaded_at = datetime.datetime.utcfromtimestamp(uploaded_t)
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


def launch_object_detection_job(barcode: str, image_url: str, server_domain: str):
    send_ipc_event(
        "object_detection",
        {"barcode": barcode, "image_url": image_url, "server_domain": server_domain},
    )


def run_object_detection(barcode: str, image_url: str, server_domain: str):
    source_image = get_source_from_image_url(image_url)
    image_instance = ImageModel.get_or_none(source_image=source_image)

    if image_instance is None:
        logger.warning("Missing image in DB for image {}".format(image_url))
        return

    timestamp = datetime.datetime.utcnow()
    results = predict_objects(barcode, image_url, server_domain)

    logos = []
    for model_name, result in results.items():
        data = result.to_json(threshold=0.1)
        max_confidence = max([item["score"] for item in data], default=None)
        image_prediction = ImagePrediction.create(
            image=image_instance,
            type="object_detection",
            model_name=model_name,
            model_version=settings.OBJECT_DETECTION_MODEL_VERSION[model_name],
            data={"objects": data},
            timestamp=timestamp,
            max_confidence=max_confidence,
        )
        for i, item in enumerate(data):
            if item["score"] >= 0.5:
                logo = LogoAnnotation.create(
                    image_prediction=image_prediction,
                    index=i,
                    score=item["score"],
                    bounding_box=item["bounding_box"],
                )
                logos.append(logo)

    if logos:
        add_logos_to_ann(image_instance, logos)
        save_nearest_neighbors(logos)

        for logo in logos:
            predict_logo_label(logo)
