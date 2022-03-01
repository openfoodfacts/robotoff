import datetime
import pathlib
from typing import Optional

import requests
from PIL import Image

from robotoff import settings
from robotoff.insights.extraction import get_predictions_from_image
from robotoff.insights.importer import import_insights
from robotoff.logos import (
    LOGO_CONFIDENCE_THRESHOLDS,
    add_logos_to_ann,
    import_logo_insights,
    save_nearest_neighbors,
)
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, db
from robotoff.off import get_server_type, get_source_from_url
from robotoff.prediction.object_detection import ObjectDetectionModelRegistry
from robotoff.prediction.types import PredictionType
from robotoff.products import Product, get_product_store
from robotoff.slack import NotifierFactory
from robotoff.utils import get_image_from_url, get_logger, http_session

logger = get_logger(__name__)


def run_import_image_job(
    barcode: str, image_url: str, ocr_url: str, server_domain: str
):
    logger.info(
        f"Running `import_image` for product {barcode} ({server_domain}), image {image_url}"
    )
    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        return

    source_image = get_source_from_url(image_url)

    product = get_product_store()[barcode]
    if product is None:
        logger.warning(
            f"Product {barcode} does not exist during image import ({source_image})"
        )
        return

    with db:
        with db.atomic():
            save_image(barcode, source_image, product, server_domain)
            import_insights_from_image(
                barcode, image, source_image, ocr_url, server_domain
            )
        with db.atomic():
            # Launch object detection in a new SQL transaction
            run_object_detection(barcode, image, source_image, server_domain)


def import_insights_from_image(
    barcode: str,
    image: Image.Image,
    source_image: str,
    ocr_url: str,
    server_domain: str,
):
    predictions_all = get_predictions_from_image(barcode, image, source_image, ocr_url)
    NotifierFactory.get_notifier().notify_image_flag(
        [p for p in predictions_all if p.type == PredictionType.image_flag],
        source_image,
        barcode,
    )
    imported = import_insights(predictions_all, server_domain, automatic=True)
    logger.info(f"Import finished, {imported} insights imported")


def save_image(
    barcode: str, source_image: str, product: Product, server_domain: str
) -> Optional[ImageModel]:
    """Save imported image details in DB."""
    image_id = pathlib.Path(source_image).stem

    if not image_id.isdigit():
        logger.warning("Non raw image was sent: %s", source_image)
        return None

    if image_id not in product.images:
        logger.warning("Unknown image for product %s: %s", barcode, source_image)
        return None

    image = product.images[image_id]
    sizes = image.get("sizes", {}).get("full")

    if not sizes:
        logger.warning("Image with missing size information: %s", image)
        return None

    width = sizes["w"]
    height = sizes["h"]

    if "uploaded_t" not in image:
        logger.warning("Missing uploaded_t field: %s", list(image))
        return None

    uploaded_t = image["uploaded_t"]
    if isinstance(uploaded_t, str):
        if not uploaded_t.isdigit():
            logger.warning("Non digit uploaded_t value: %s", uploaded_t)
            return None

        uploaded_t = int(uploaded_t)

    uploaded_at = datetime.datetime.utcfromtimestamp(uploaded_t)
    image_model = ImageModel.create(
        barcode=barcode,
        image_id=image_id,
        width=width,
        height=height,
        source_image=source_image,
        uploaded_at=uploaded_at,
        server_domain=server_domain,
        server_type=get_server_type(server_domain).name,
    )
    if image_model is not None:
        logger.info("New image %s created in DB", image_model.id)
    return image_model


def run_object_detection(
    barcode: str, image: Image.Image, source_image: str, server_domain: str
):
    """Detect logos using the universal logo detector model and generate
    logo-related insights.

    :param barcode: Product barcode
    :param image: Pillow Image to run the object detection on
    :param image_url: URL of the image to use
    :param server_domain: The server domain associated with the image
    """
    logger.info(
        f"Running object detection for product {barcode} ({server_domain}), "
        f"image {source_image}"
    )
    image_instance = ImageModel.get_or_none(source_image=source_image)

    if image_instance is None:
        logger.warning(f"Missing image in DB for image {source_image}")
        return

    timestamp = datetime.datetime.utcnow()
    model_name = "universal-logo-detector"
    results = ObjectDetectionModelRegistry.get(model_name).detect_from_image(
        image, output_image=False
    )
    data = results.to_json(threshold=0.1)
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

    logos = []
    for i, item in enumerate(data):
        if item["score"] >= 0.5:
            logo = LogoAnnotation.create(
                image_prediction=image_prediction,
                index=i,
                score=item["score"],
                bounding_box=item["bounding_box"],
            )
            logos.append(logo)

    logger.info(f"{len(logos)} logos found for image {source_image}")
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
