import datetime
import pathlib
from typing import List, Optional

import requests

from robotoff import settings
from robotoff.insights._enum import InsightType
from robotoff.insights.extraction import (
    get_insights_from_image,
    get_source_from_image_url,
    predict_objects,
)
from robotoff.insights.importer import BaseInsightImporter, InsightImporterFactory
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
from robotoff.off import get_server_type
from robotoff.products import Product, get_product_store
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


def add_logos_to_ann(image: ImageModel, logos: List[LogoAnnotation]) -> int:
    if not logos:
        return 0

    image_url = settings.OFF_IMAGE_BASE_URL + image.source_image

    data = {
        "image_url": image_url,
        "logos": [{"bounding_box": logo.bounding_box, "id": logo.id} for logo in logos],
    }
    r = requests.post(
        "https://robotoff.openfoodfacts.org/api/v1/ann/add", json=data, timeout=30
    )

    if not r.ok:
        logger.warning(f"error while adding image to ANN ({r.status_code}): {r.text}")
        return 0

    return r.json()["added"]


def save_nearest_neighbors(logos: List[LogoAnnotation]) -> int:
    logo_ids_params = ",".join((str(logo.id) for logo in logos))
    r = requests.get(
        f"https://robotoff.openfoodfacts.org/api/v1/ann/batch?logo_ids={logo_ids_params}",
        timeout=30,
    )

    response = r.json()
    results = {int(key): value for key, value in response["results"].items()}

    logo_id_to_logo = {logo.id: logo for logo in logos}
    missing_logo_ids = set(logo_id_to_logo.keys()).difference(set(results.keys()))

    if missing_logo_ids:
        logger.warning(f"Missing logo IDs in response: {missing_logo_ids}")

    saved = 0
    for logo_id, logo_results in results.items():
        if logo_id in logo_id_to_logo:
            logo = logo_id_to_logo[logo_id]
            distances = [n["distance"] for n in logo_results]
            logo_ids = [n["logo_id"] for n in logo_results]
            logo.nearest_neighbors = {
                "distances": distances,
                "logo_ids": logo_ids,
            }
            logo.save()
            saved += 1

    return saved
