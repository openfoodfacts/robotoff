from pathlib import Path
from typing import Optional

import elasticsearch
from elasticsearch.helpers import BulkIndexError
from PIL import Image

from robotoff import settings
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
from robotoff.off import generate_image_url, get_source_from_url
from robotoff.products import get_product_store
from robotoff.slack import NotifierFactory
from robotoff.triton import generate_clip_embedding
from robotoff.types import (
    JSONType,
    ObjectDetectionModel,
    PredictionType,
    ProductIdentifier,
    ServerType,
)
from robotoff.utils import get_image_from_url, get_logger, http_session
from robotoff.workers.queues import enqueue_job, high_queue

logger = get_logger(__name__)


def run_import_image_job(product_id: ProductIdentifier, image_url: str, ocr_url: str):
    """This job is triggered every time there is a new OCR image available for
    processing by Robotoff, via /api/v1/images/import.

    On each image import, Robotoff performs the following tasks:

    1. Generates various predictions based on the OCR-extracted text from the image.
    2. Extracts the nutriscore prediction based on the nutriscore ML model.
    3. Triggers the 'object_detection' task
    4. Stores the imported image metadata in the Robotoff DB.
    """
    logger.info("Running `import_image` for %s, image %s", product_id, image_url)
    source_image = get_source_from_url(image_url)
    product = get_product_store(product_id.server_type)[product_id]
    if product is None and settings.ENABLE_PRODUCT_CHECK:
        logger.info(
            "%s does not exist during image import (%s)",
            product_id,
            source_image,
        )
        return

    product_images: Optional[JSONType] = getattr(product, "images", None)
    with db:
        image_model = save_image(product_id, source_image, image_url, product_images)

        if image_model is None:
            # The image is invalid, no need to perform image extraction jobs
            return

        if image_model.deleted:
            return

        image_id = Path(source_image).stem
        if product_images is not None and image_id not in product_images:
            # It happens when the image has been deleted after Robotoff import
            logger.info("Unknown image for %s: %s", product_id, source_image)
            image_model.deleted = True
            ImageModel.bulk_update([image_model], fields=["deleted"])
            return

    if product_id.server_type.is_food():
        # Currently we don't support insight generation for projects other
        # than OFF (OBF, OPF,...)
        enqueue_job(
            import_insights_from_image,
            high_queue,
            job_kwargs={"result_ttl": 0},
            product_id=product_id,
            image_url=image_url,
            ocr_url=ocr_url,
        )
    # The two following tasks take longer than the previous one, so it
    # shouldn't be an issue to launch tasks concurrently (and we still have
    # the insight import lock to avoid concurrent insight import in DB for the
    # same product)
    enqueue_job(
        run_logo_object_detection,
        high_queue,
        job_kwargs={"result_ttl": 0},
        product_id=product_id,
        image_url=image_url,
    )
    # Nutrition table detection is not used at the moment, and every new image
    # is costly in CPU (as we perform object detection)
    # Disable it until we either need it or get a GPU server
    # enqueue_job(
    #     run_nutrition_table_object_detection,
    #     high_queue,
    #     job_kwargs={"result_ttl": 0},
    #     product_id=product_id,
    #     image_url=image_url,
    # )


def import_insights_from_image(
    product_id: ProductIdentifier, image_url: str, ocr_url: str
):
    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)
    predictions = extract_ocr_predictions(
        product_id, ocr_url, DEFAULT_OCR_PREDICTION_TYPES
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
            product_id=product_id,
            image_url=image_url,
        )
    NotifierFactory.get_notifier().notify_image_flag(
        [p for p in predictions if p.type == PredictionType.image_flag],
        source_image,
        product_id,
    )

    with db:
        import_result = import_insights(predictions, server_type=product_id.server_type)
        logger.info(import_result)


def save_image_job(batch: list[tuple[ProductIdentifier, str]], server_type: ServerType):
    """Save a batch of images in DB.

    :param batch: a batch of (product_id, source_image) tuples
    :param server_type: the server type (project) of the products
    """
    product_store = get_product_store(server_type)
    with db.connection_context():
        for product_id, source_image in batch:
            product = product_store[product_id]
            if product is None and settings.ENABLE_PRODUCT_CHECK:
                continue

            with db.atomic():
                image_url = generate_image_url(product_id, Path(source_image).stem)
                save_image(
                    product_id,
                    source_image,
                    image_url,
                    getattr(product, "images", None),
                )


def run_nutrition_table_object_detection(product_id: ProductIdentifier, image_url: str):
    logger.info(
        "Running nutrition table object detection for %s, image %s",
        product_id,
        image_url,
    )

    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    with db:
        if image_model := ImageModel.get_or_none(
            source_image=source_image, server_type=product_id.server_type.name
        ):
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


def run_nutriscore_object_detection(product_id: ProductIdentifier, image_url: str):
    logger.info(
        "Running nutriscore object detection for %s, image %s", product_id, image_url
    )

    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    with db:
        if (
            image_model := ImageModel.get_or_none(
                source_image=source_image, server_type=product_id.server_type.name
            )
        ) is None:
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
            barcode=product_id.barcode,
            source_image=source_image,
            value_tag=label_tag,
            automatic_processing=False,
            server_type=product_id.server_type,
            predictor="nutriscore",
            data={"bounding_box": result["bounding_box"]},
            confidence=score,
        )
        import_result = import_insights([prediction], product_id.server_type)
        logger.info(import_result)


def run_logo_object_detection(product_id: ProductIdentifier, image_url: str):
    """Detect logos using the universal logo detector model and generate
    logo-related predictions.

    :param product_id: identifier of the product
    :param image_url: URL of the image to use
    """
    logger.info("Running logo object detection for %s, image %s", product_id, image_url)

    image = get_image_from_url(image_url, error_raise=False, session=http_session)

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    with db:
        if (
            image_model := ImageModel.get_or_none(
                source_image=source_image, server_type=product_id.server_type.name
            )
        ) is None:
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
            server_type=product_id.server_type,
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
def process_created_logos(image_prediction_id: int, server_type: ServerType):
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
        add_logos_to_ann(es_client, logo_embeddings, server_type)
    except BulkIndexError as e:
        logger.info("Request error during logo addition to ANN", exc_info=e)
        return

    try:
        save_nearest_neighbors(es_client, logo_embeddings, server_type)
    except (elasticsearch.ConnectionError, elasticsearch.ConnectionTimeout) as e:
        logger.info("Request error during ANN batch query", exc_info=e)
        return

    if server_type.is_food():
        # We don't support annotation on projects other than off/off_pro
        # currently
        logos = [embedding.logo for embedding in logo_embeddings]
        thresholds = get_logo_confidence_thresholds()
        import_logo_insights(logos, thresholds=thresholds, server_type=server_type)
