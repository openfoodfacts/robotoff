import datetime
import pathlib
from typing import Optional

from PIL import Image
from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import HTTPError, Timeout

from robotoff.insights.extraction import (
    DEFAULT_OCR_PREDICTION_TYPES,
    extract_ocr_predictions,
    run_object_detection_model,
)
from robotoff.insights.importer import import_insights
from robotoff.logos import (
    add_logos_to_ann,
    filter_logos,
    get_logo_confidence_thresholds,
    import_logo_insights,
    save_nearest_neighbors,
)
from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    LogoEmbedding,
    Prediction,
    db,
    with_db,
)
from robotoff.off import get_server_type, get_source_from_url
from robotoff.products import Product, get_product_store
from robotoff.slack import NotifierFactory
from robotoff.triton import generate_clip_embedding
from robotoff.types import ObjectDetectionModel, PredictionType
from robotoff.utils import get_image_from_url, get_logger, http_session
from robotoff.workers.queues import enqueue_job, high_queue

logger = get_logger(__name__)


def run_import_image_job(
    barcode: str, image_url: str, ocr_url: str, server_domain: str
):
    """This job is triggered every time there is a new OCR image available for
    processing by Robotoff, via /api/v1/images/import.

    On each image import, Robotoff performs the following tasks:

    1. Generates various predictions based on the OCR-extracted text from the image.
    2. Extracts the nutriscore prediction based on the nutriscore ML model.
    3. Triggers the 'object_detection' task
    4. Stores the imported image metadata in the Robotoff DB.
    """
    logger.info(
        f"Running `import_image` for product {barcode} ({server_domain}), image {image_url}"
    )
    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    product = get_product_store()[barcode]
    if product is None:
        logger.info(
            "Product %s does not exist during image import (%s)", barcode, source_image
        )
        return

    with db:
        save_image(barcode, source_image, product, server_domain)

    enqueue_job(
        import_insights_from_image,
        high_queue,
        barcode=barcode,
        image_url=image_url,
        ocr_url=ocr_url,
        server_domain=server_domain,
    )
    # The two following tasks take longer than the previous one, so it
    # shouldn't be an issue to launch tasks concurrently (and we still have
    # the insight import lock to avoid concurrent insight import in DB for the
    # same product)
    enqueue_job(
        run_logo_object_detection,
        high_queue,
        barcode=barcode,
        image_url=image_url,
        server_domain=server_domain,
    )
    enqueue_job(
        run_nutrition_table_object_detection,
        high_queue,
        barcode=barcode,
        image_url=image_url,
        server_domain=server_domain,
    )


def import_insights_from_image(
    barcode: str,
    image_url: str,
    ocr_url: str,
    server_domain: str,
):
    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)
    predictions = extract_ocr_predictions(
        barcode, ocr_url, DEFAULT_OCR_PREDICTION_TYPES
    )
    if any(
        prediction.value_tag == "en:nutriscore"
        and prediction.type == PredictionType.label
        for prediction in predictions
    ):
        enqueue_job(
            run_nutriscore_object_detection,
            high_queue,
            barcode=barcode,
            image_url=image_url,
            server_domain=server_domain,
        )
    NotifierFactory.get_notifier().notify_image_flag(
        [p for p in predictions if p.type == PredictionType.image_flag],
        source_image,
        barcode,
    )

    with db:
        imported = import_insights(predictions, server_domain)
        logger.info("Import finished, %s insights imported", imported)


def save_image_job(batch: list[tuple[str, str]], server_domain: str):
    """Save a batch of images in DB.

    :param batch: a batch of (barcode, source_image) tuples
    :param server_domain: the server domain to use
    """
    with db.connection_context():
        for barcode, source_image in batch:
            product = get_product_store()[barcode]
            if product is None:
                continue

            with db.atomic():
                save_image(barcode, source_image, product, server_domain)


def save_image(
    barcode: str, source_image: str, product: Product, server_domain: str
) -> Optional[ImageModel]:
    """Save imported image details in DB."""
    if existing_image_model := ImageModel.get_or_none(source_image=source_image):
        logger.info(
            f"Image {source_image} already exist in DB, returning existing image",
        )
        return existing_image_model

    image_id = pathlib.Path(source_image).stem

    if not image_id.isdigit():
        logger.info("Non raw image was sent: %s", source_image)
        return None

    if image_id not in product.images:
        logger.info("Unknown image for product %s: %s", barcode, source_image)
        return None

    image = product.images[image_id]
    sizes = image.get("sizes", {}).get("full")

    if not sizes:
        logger.info("Image with missing size information: %s", image)
        return None

    width = sizes["w"]
    height = sizes["h"]

    if "uploaded_t" not in image:
        logger.info("Missing uploaded_t field: %s", list(image))
        return None

    uploaded_t = image["uploaded_t"]
    if isinstance(uploaded_t, str):
        if not uploaded_t.isdigit():
            logger.info("Non digit uploaded_t value: %s", uploaded_t)
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


def run_nutrition_table_object_detection(
    barcode: str, image_url: str, server_domain: str
):
    logger.info(
        f"Running nutrition table object detection for product {barcode} "
        f"({server_domain}), image {image_url}"
    )

    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    with db:
        run_object_detection_model(
            ObjectDetectionModel.nutrition_table, image, source_image
        )


NUTRISCORE_LABELS = {
    "nutriscore-a": "en:nutriscore-grade-a",
    "nutriscore-b": "en:nutriscore-grade-b",
    "nutriscore-c": "en:nutriscore-grade-c",
    "nutriscore-d": "en:nutriscore-grade-d",
    "nutriscore-e": "en:nutriscore-grade-e",
}


def run_nutriscore_object_detection(barcode: str, image_url: str, server_domain: str):
    logger.info(
        f"Running nutriscore object detection for product {barcode} "
        f"({server_domain}), image {image_url}"
    )

    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    with db:
        image_prediction = run_object_detection_model(
            ObjectDetectionModel.nutriscore, image, source_image
        )

    if not image_prediction:
        return

    results = [
        item for item in image_prediction.data["objects"] if item["score"] >= 0.5
    ]

    if not results:
        return

    if len(results) > 1:
        logger.info("more than one nutriscore detected, discarding detections")
        return

    result = results[0]
    score = result["score"]
    label_tag = NUTRISCORE_LABELS[result["label"]]

    with db:
        prediction = Prediction(
            type=PredictionType.label,
            barcode=barcode,
            source_image=source_image,
            value_tag=label_tag,
            automatic_processing=False,
            server_domain=server_domain,
            predictor="nutriscore",
            data={
                "confidence": score,
                "bounding_box": result["bounding_box"],
            },
        )
        import_insights([prediction], server_domain)


def run_logo_object_detection(
    barcode: str, image_url: str, server_domain: str, process_logos: bool = True
):
    """Detect logos using the universal logo detector model and generate
    logo-related predictions.

    :param barcode: Product barcode
    :param image_url: URL of the image to use
    :param server_domain: The server domain associated with the image
    :param process_logos: if True, process created logos: send them to
      Robotoff ANN and fetch nearest neighbors
    """
    logger.info(
        f"Running logo object detection for product {barcode} "
        f"({server_domain}), image {image_url}"
    )

    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    with db:
        image_prediction = run_object_detection_model(
            ObjectDetectionModel.universal_logo_detector, image, source_image
        )

        if image_prediction is None:
            # Can occur in normal conditions if an image prediction
            # already exists for this image and model
            return

        logos: list[LogoAnnotation] = []
        for i, item in filter_logos(
            image_prediction.data["objects"],
            score_threshold=0.5,
            iou_threshold=0.95,
        ):
            logos.append(
                LogoAnnotation.create(
                    image_prediction=image_prediction,
                    index=i,
                    score=item["score"],
                    bounding_box=item["bounding_box"],
                )
            )

    logger.info("%s logos found for image %s", len(logos), source_image)
    if logos and process_logos:
        with db:
            save_logo_embeddings(logos, image)
        enqueue_job(
            process_created_logos,
            high_queue,
            job_kwargs={},
            image_prediction_id=image_prediction.id,
            server_domain=server_domain,
        )


def save_logo_embeddings(logos: list[LogoAnnotation], image: Image.Image):
    """Generate logo embeddings using CLIP model and save them in
    logo_embedding table."""
    cropped_images = []
    for logo in logos:
        y_min, x_min, y_max, x_max = logo.bounding_box
        (left, right, top, bottom) = (
            x_min * image.width,
            x_max * image.width,
            y_min * image.height,
            y_max * image.height,
        )
        cropped_images = image.crop((left, top, right, bottom))
    embeddings = generate_clip_embedding(cropped_images)

    with db:
        for i in range(len(logos)):
            logo_id = logos[i].id
            logo_embedding = embeddings[i]
            LogoEmbedding.create(logo_id=logo_id, embedding=logo_embedding.tobytes())


@with_db
def process_created_logos(image_prediction_id: int, server_domain: str):
    logos = (
        LogoAnnotation.select()
        .join(ImagePrediction)
        .join(ImageModel)
        .switch(LogoAnnotation)
        .join(LogoEmbedding)
        .where(ImagePrediction.id == image_prediction_id)
    )

    if not logos:
        return

    image_instance = logos[0].image_prediction.image

    try:
        add_logos_to_ann(image_instance, logos)
    except (RequestConnectionError, HTTPError, Timeout) as e:
        logger.info("Request error during logo addition to ANN", exc_info=e)
        return

    try:
        save_nearest_neighbors(logos)
    except (RequestConnectionError, HTTPError, Timeout) as e:
        logger.info("Request error during ANN batch query", exc_info=e)
        return

    thresholds = get_logo_confidence_thresholds()
    import_logo_insights(logos, thresholds=thresholds, server_domain=server_domain)
