import datetime
import pathlib
from typing import Optional

import requests

from robotoff import settings
from robotoff.insights.dataclass import InsightType
from robotoff.insights.extraction import (
    get_predictions_from_image,
    get_source_from_image_url,
    predict_objects,
)
from robotoff.insights.importer import BaseInsightImporter, InsightImporterFactory
from robotoff.logos import (
    LOGO_CONFIDENCE_THRESHOLDS,
    add_logos_to_ann,
    import_logo_insights,
    save_nearest_neighbors,
)
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
from robotoff.off import get_server_type
from robotoff.prediction.types import PredictionType
from robotoff.products import Product, get_product_store
from robotoff.slack import NotifierFactory
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
    predictions_all = get_predictions_from_image(barcode, image_url, ocr_url)

    for prediction_type, product_predictions in predictions_all.items():
        if prediction_type == PredictionType.image_flag:
            NotifierFactory.get_notifier().notify_image_flag(
                product_predictions.predictions,
                product_predictions.source_image,  # type: ignore
                product_predictions.barcode,
            )
            continue

        logger.info("Extracting {}".format(prediction_type.name))
        importer: BaseInsightImporter = InsightImporterFactory.create(
            InsightType[prediction_type], product_store
        )

        with db.atomic():
            imported = importer.import_insights(
                [product_predictions], server_domain=server_domain, automatic=True
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

        try:
            save_nearest_neighbors(logos)
        except requests.exceptions.HTTPError as e:
            resp = e.response
            logger.warning(
                f"Could not save nearest neighbors in ANN: {resp.status_code}: {resp.text}"
            )

        thresholds = LOGO_CONFIDENCE_THRESHOLDS.get()
        import_logo_insights(logos, thresholds=thresholds, server_domain=server_domain)
