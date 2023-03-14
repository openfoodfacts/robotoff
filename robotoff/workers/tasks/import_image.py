from pathlib import Path

import elasticsearch
from elasticsearch.helpers import BulkIndexError
from PIL import Image

from robotoff.elasticsearch.client import get_es_client
from robotoff.images import save_image
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
from robotoff.off import get_source_from_url
from robotoff.products import get_product_store
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
    source_image = get_source_from_url(image_url)
    product = get_product_store()[barcode]
    if product is None:
        logger.info(
            "Product %s does not exist during image import (%s)", barcode, source_image
        )
        return

    with db:
        image_model = save_image(barcode, source_image, product.images, server_domain)

        if image_model is None:
            # The image is invalid, no need to perform image extraction jobs
            return

        if image_model.deleted:
            return

        image_id = Path(source_image).stem
        if image_id not in product.images:
            # It happens when the image has been deleted after Robotoff import
            logger.info("Unknown image for product %s: %s", barcode, source_image)
            image_model.deleted = True
            ImageModel.bulk_update([image_model], fields=["deleted"])
            return

    enqueue_job(
        import_insights_from_image,
        high_queue,
        job_kwargs={"result_ttl": 0},
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
        job_kwargs={"result_ttl": 0},
        barcode=barcode,
        image_url=image_url,
        server_domain=server_domain,
    )
    # Nutrition table detection is not used at the moment, and every new image
    # is costly in CPU (as we perform object detection)
    # Disable it until we either need it or get a GPU server
    # enqueue_job(
    #     run_nutrition_table_object_detection,
    #     high_queue,
    #     job_kwargs={"result_ttl": 0},
    #     barcode=barcode,
    #     image_url=image_url,
    #     server_domain=server_domain,
    # )


def import_insights_from_image(
    barcode: str, image_url: str, ocr_url: str, server_domain: str
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
            job_kwargs={"result_ttl": 0},
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
        import_result = import_insights(predictions, server_domain)
        logger.info(import_result)


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
                save_image(barcode, source_image, product.images, server_domain)


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
        if image_model := ImageModel.get_or_none(source_image=source_image):
            run_object_detection_model(
                ObjectDetectionModel.nutrition_table, image, image_model
            )
        else:
            logger.info("Missing image in DB for image %s", source_image)


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
        if (image_model := ImageModel.get_or_none(source_image=source_image)) is None:
            logger.info("Missing image in DB for image %s", source_image)
            return

        image_prediction = run_object_detection_model(
            ObjectDetectionModel.nutriscore, image, image_model
        )

    if image_prediction is None:
        # an ImagePrediction already exist
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
            data={"bounding_box": result["bounding_box"]},
            confidence=score,
        )
        import_result = import_insights([prediction], server_domain)
        logger.info(import_result)


def run_logo_object_detection(barcode: str, image_url: str, server_domain: str):
    """Detect logos using the universal logo detector model and generate
    logo-related predictions.

    :param barcode: Product barcode
    :param image_url: URL of the image to use
    :param server_domain: The server domain associated with the image
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
        if (image_model := ImageModel.get_or_none(source_image=source_image)) is None:
            logger.info("Missing image in DB for image %s", source_image)
            return

        image_prediction: ImagePrediction = run_object_detection_model(  # type: ignore
            ObjectDetectionModel.universal_logo_detector,
            image,
            image_model,
            return_null_if_exist=False,
        )
        existing_logos = list(image_prediction.logos)

        if not existing_logos:
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
                        barcode=image_model.barcode,
                        source_image=image_model.source_image,
                    )
                )
            logger.info("%s logos found for image %s", len(logos), source_image)
        else:
            # Logos already exist for this image prediction, we just make sure embeddings
            # are in DB as well
            logos = [
                existing_logo
                for existing_logo in existing_logos
                if len(list(existing_logo.embeddings)) == 0
            ]

    if logos:
        with db.connection_context():
            save_logo_embeddings(logos, image)
        enqueue_job(
            process_created_logos,
            high_queue,
            job_kwargs={"result_ttl": 0},
            image_prediction_id=image_prediction.id,
            server_domain=server_domain,
        )


def save_logo_embeddings(logos: list[LogoAnnotation], image: Image.Image):
    """Generate logo embeddings using CLIP model and save them in
    logo_embedding table."""
    resized_cropped_images = []
    for logo in logos:
        y_min, x_min, y_max, x_max = logo.bounding_box
        (left, right, top, bottom) = (
            x_min * image.width,
            x_max * image.width,
            y_min * image.height,
            y_max * image.height,
        )
        cropped_image = image.crop((left, top, right, bottom))
        resized_cropped_images.append(cropped_image.resize((224, 224)))
    embeddings = generate_clip_embedding(resized_cropped_images)

    with db.atomic():
        for i in range(len(logos)):
            logo_id = logos[i].id
            logo_embedding = embeddings[i]
            LogoEmbedding.create(logo_id=logo_id, embedding=logo_embedding.tobytes())


@with_db
def process_created_logos(image_prediction_id: int, server_domain: str):
    logo_embeddings = list(
        LogoEmbedding.select()
        .join(LogoAnnotation)
        .join(ImagePrediction)
        .where(ImagePrediction.id == image_prediction_id)
    )

    if not logo_embeddings:
        return

    es_client = get_es_client()
    try:
        add_logos_to_ann(es_client, logo_embeddings)
    except BulkIndexError as e:
        logger.info("Request error during logo addition to ANN", exc_info=e)
        return

    try:
        save_nearest_neighbors(es_client, logo_embeddings)
    except (elasticsearch.ConnectionError, elasticsearch.ConnectionTimeout) as e:
        logger.info("Request error during ANN batch query", exc_info=e)
        return

    logos = [embedding.logo for embedding in logo_embeddings]

    thresholds = get_logo_confidence_thresholds()
    import_logo_insights(logos, thresholds=thresholds, server_domain=server_domain)
