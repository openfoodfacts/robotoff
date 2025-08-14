import copy
import dataclasses
import datetime
import logging
from pathlib import Path

import elasticsearch
import numpy as np
from elasticsearch.helpers import BulkIndexError
from openfoodfacts import OCRResult
from openfoodfacts.taxonomy import Taxonomy
from openfoodfacts.types import TaxonomyType
from PIL import Image

from robotoff import settings
from robotoff.elasticsearch import get_es_client
from robotoff.images import add_image_fingerprint, save_image
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
    db,
    with_db,
)
from robotoff.notifier import NotifierFactory
from robotoff.off import (
    generate_image_url,
    generate_json_ocr_url,
    get_source_from_url,
    parse_ingredients,
)
from robotoff.prediction import ingredient_list, nutrition_extraction
from robotoff.prediction.upc_image import UPCImageType, find_image_is_upc
from robotoff.products import get_product_store
from robotoff.taxonomy import get_taxonomy
from robotoff.triton import (
    GRPCInferenceServiceStub,
    generate_clip_embedding,
    get_triton_inference_stub,
)
from robotoff.types import (
    ImportImageFlag,
    JSONType,
    ObjectDetectionModel,
    Prediction,
    PredictionType,
    ProductIdentifier,
    ServerType,
)
from robotoff.utils import get_image_from_url, http_session
from robotoff.utils.image import (
    convert_bounding_box_absolute_to_relative,
    convert_image_to_array,
)
from robotoff.workers.queues import enqueue_job, get_high_queue, low_queue
from robotoff.workers.tasks.common import add_category_insight_job

logger = logging.getLogger(__name__)


@with_db
def rerun_import_all_images(
    limit: int | None = None,
    server_type: ServerType | None = None,
    return_count: bool = False,
    flags: list[ImportImageFlag] | None = None,
) -> None | int:
    """Rerun full image import on all images in DB.

    This includes launching all ML models and insight extraction from the image and
    associated OCR. To control which tasks are rerun, use the --flags option.

    :param limit: the maximum number of images to process, defaults to None (all)
    :param server_type: the server type (project) of the products, defaults to None
        (all)
    :param return_count: if True, return the number of images to process, without
        processing them, defaults to False
    :param flags: the list of flags to rerun, defaults to None (all)
    :return: the number of images to process, or None if return_count is False
    """
    where_clauses = [ImageModel.deleted == False]  # noqa: E712

    if server_type is not None:
        where_clauses.append(ImageModel.server_type == server_type.name)
    query = (
        ImageModel.select(
            ImageModel.id,
            ImageModel.barcode,
            ImageModel.image_id,
            ImageModel.server_type,
        )
        .where(*where_clauses)
        .order_by(ImageModel.uploaded_at.desc())
        .tuples()
    )
    if limit:
        query = query.limit(limit)

    if return_count:
        return query.count()

    for image_model_id, barcode, image_id, server_type_str in query:
        if not isinstance(barcode, str) and not barcode.isdigit():
            raise ValueError("Invalid barcode: %s" % barcode)

        product_id = ProductIdentifier(barcode, ServerType[server_type_str])
        image_url = generate_image_url(product_id, image_id)
        ocr_url = generate_json_ocr_url(product_id, image_id)
        run_import_image(
            product_id=product_id,
            image_model_id=image_model_id,
            image_url=image_url,
            ocr_url=ocr_url,
            flags=flags,
            # Use the low queue for rerun, as it's not as important as the
            # real-time updates from Redis
            use_high_queue=False,
        )
    return None


def run_import_image_job(
    product_id: ProductIdentifier,
    image_url: str,
    ocr_url: str,
    flags: list[ImportImageFlag] | None = None,
) -> None:
    """This job is triggered every time there is a new OCR image available for
    processing by Robotoff, via an event published on the Redis stream.

    On each image import, Robotoff performs the following tasks:

    1. Generates various predictions based on the OCR-extracted text from the
       image.
    2. Extracts the nutriscore prediction based on the nutriscore ML model.
    3. Triggers the 'object_detection' task
    4. Stores the imported image metadata in the Robotoff DB.
    5. Compute image fingerprint, for duplicate image detection.

    What tasks are performed can be controlled using the `flags` parameter. By
    default, all tasks are performed. A new rq job is enqueued for each task.

    Before running the tasks, the image is downloaded and stored in the Robotoff
    DB.

    :param product_id: the product identifier
    :param image_url: the URL of the image to import
    :param ocr_url: the URL of the OCR JSON file
    :param flags: the list of flags to run, defaults to None (all)
    """
    logger.info("Running `import_image` for %s, image %s", product_id, image_url)

    source_image = get_source_from_url(image_url)
    product = get_product_store(product_id.server_type)[product_id]
    if product is None and settings.ENABLE_MONGODB_ACCESS:
        logger.info(
            "%s does not exist during image import (%s)",
            product_id,
            source_image,
        )
        return

    product_images: JSONType | None = getattr(product, "images", None)
    with db:
        image_model = save_image(
            product_id, source_image, image_url, product_images, use_cache=True
        )

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

    run_import_image(
        product_id=product_id,
        image_model_id=image_model.id,
        image_url=image_url,
        ocr_url=ocr_url,
        flags=flags,
    )


def run_import_image(
    product_id: ProductIdentifier,
    image_model_id: int,
    image_url: str,
    ocr_url: str,
    flags: list[ImportImageFlag] | None = None,
    use_high_queue: bool = True,
) -> None:
    """Launch all extraction tasks on an image.

    We assume that the image exists in the Robotoff DB.

    What tasks are performed can be controlled using the `flags` parameter. By
    default, all tasks are performed. A new rq job is enqueued for each task.

    :param product_id: the product identifier
    :param image_model_id: the DB ID of the image
    :param image_url: the URL of the image to import
    :param ocr_url: the URL of the OCR JSON file
    :param flags: the list of flags to run, defaults to None (all)
    param use_high_queue: if True, use the high priority queue for most important
        tasks. If False, always use the low priority queue. Defaults to True.
    """
    if flags is None:
        flags = [flag for flag in ImportImageFlag]

    high_queue = get_high_queue(product_id) if use_high_queue else low_queue

    if ImportImageFlag.add_image_fingerprint in flags:
        # Compute image fingerprint, this job is low priority
        enqueue_job(
            add_image_fingerprint_job,
            low_queue,
            job_kwargs={"result_ttl": 0},
            image_model_id=image_model_id,
        )

    if product_id.server_type.is_food():
        if ImportImageFlag.import_insights_from_image in flags:
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

        if ImportImageFlag.extract_ingredients in flags:
            # Only extract ingredient lists for food products, as the model was not
            # trained on non-food products
            enqueue_job(
                extract_ingredients_job,
                high_queue,
                # We add a higher timeout, as we request Product Opener to
                # parse ingredient list, which may take a while depending on
                # the number of ingredient list (~1s per ingredient list)
                job_kwargs={"result_ttl": 0, "timeout": "2m"},
                product_id=product_id,
                ocr_url=ocr_url,
            )

        if ImportImageFlag.extract_nutrition in flags:
            enqueue_job(
                extract_nutrition_job,
                high_queue,
                job_kwargs={"result_ttl": 0, "timeout": "2m"},
                product_id=product_id,
                image_url=image_url,
                ocr_url=ocr_url,
            )

        if ImportImageFlag.predict_category in flags:
            # Predict category using the neural model
            # Contrary to a product update, we always run the category
            # prediction job when an image is uploaded, as we use the
            # last 10 images to predict the category
            enqueue_job(
                add_category_insight_job,
                high_queue,
                job_kwargs={"result_ttl": 0, "timeout": "2m"},
                product_id=product_id,
            )

    if ImportImageFlag.run_logo_object_detection in flags:
        # We make sure there are no concurrent insight processing by sending
        # the job to the same queue. The queue is selected based on the product
        # barcode. See `get_high_queue` documentation for more details.
        enqueue_job(
            run_logo_object_detection,
            high_queue,
            job_kwargs={"result_ttl": 0},
            product_id=product_id,
            image_url=image_url,
            ocr_url=ocr_url,
        )

    if product_id.server_type.is_food():
        if ImportImageFlag.run_nutrition_table_object_detection in flags:
            # Run object detection model that detects nutrition tables
            enqueue_job(
                run_nutrition_table_object_detection,
                high_queue,
                job_kwargs={"result_ttl": 0},
                product_id=product_id,
                image_url=image_url,
            )

    # Run UPC detection to detect if the image is dominated by a UPC (and thus
    # should not be a product selected image)
    # UPC detection is buggy since the upgrade to OpenCV 4.10
    # Unit tests are failing, we need to fix them before re-enabling this task
    # enqueue_job(
    #     run_upc_detection,
    #     high_queue,
    #     job_kwargs={"result_ttl": 0},
    #     product_id=product_id,
    #     image_url=image_url,
    # )


def import_insights_from_image(
    product_id: ProductIdentifier, image_url: str, ocr_url: str
):
    image = get_image_from_url(
        image_url, error_raise=False, session=http_session, use_cache=True
    )

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
            get_high_queue(product_id),
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


def save_image_job(
    batch: list[tuple[ProductIdentifier, str]], server_type: ServerType
) -> None:
    """Save a batch of images in DB.

    :param batch: a batch of (product_id, source_image) tuples
    :param server_type: the server type (project) of the products
    """
    product_store = get_product_store(server_type)
    with db.connection_context():
        for product_id, source_image in batch:
            product = product_store[product_id]
            if product is None and settings.ENABLE_MONGODB_ACCESS:
                continue

            with db.atomic():
                image_url = generate_image_url(product_id, Path(source_image).stem)
                save_image(
                    product_id,
                    source_image,
                    image_url,
                    getattr(product, "images", None),
                    # set use_cache=False, as we process many images only once
                    use_cache=False,
                )


def run_nutrition_table_object_detection(
    product_id: ProductIdentifier, image_url: str, triton_uri: str | None = None
) -> None:
    """Detect the nutrition table in an image and generate a prediction.

    :param product_id: identifier of the product
    :param image_url: URL of the image to use
    :param triton_uri: URI of the Triton Inference Server, defaults to None. If
        not provided, the default value from settings is used.
    """
    logger.info(
        "Running nutrition table object detection for %s, image %s",
        product_id,
        image_url,
    )

    image = get_image_from_url(
        image_url, error_raise=False, session=http_session, use_cache=True
    )

    if image is None:
        logger.info("Error while downloading image %s", image_url)
        return

    source_image = get_source_from_url(image_url)

    with db:
        if image_model := ImageModel.get_or_none(
            source_image=source_image, server_type=product_id.server_type.name
        ):
            run_object_detection_model(
                ObjectDetectionModel.nutrition_table,
                image,
                image_model,
                # Use Triton Inference Server specific to the model if
                # triton_uri is not provided
                triton_uri=triton_uri or settings.TRITON_URI_NUTRITION_TABLE,
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


def run_upc_detection(product_id: ProductIdentifier, image_url: str) -> None:
    """Detect the presence of a UPC in an image and find if it takes up too
    much area.

    :param product_id: identifier of the product
    :param image_url: URL of the image to use
    """
    source_image = get_source_from_url(image_url)

    with db:
        image_model = ImageModel.get_or_none(
            source_image=source_image, server_type=product_id.server_type.name
        )

        if not image_model:
            logger.info("Missing image in DB for image %s", source_image)
            return

        MODEL_NAME = "upc-opencv"
        MODEL_VERSION = "upc-opencv-1.0"
        if (
            image_prediction := ImagePrediction.get_or_none(
                image=image_model, model_name=MODEL_NAME
            )
        ) is not None:
            # Image prediction already exists, uses it instead of
            # recomputing whether the image is on the image or not
            area = image_prediction.data["area"]
            # Convert string back to UPCImageType
            prediction_class = UPCImageType[image_prediction.data["class"]]
            polygon = image_prediction.data["polygon"]
        else:
            # run upc detection
            if (
                image := get_image_from_url(
                    image_url, error_raise=False, session=http_session, use_cache=True
                )
            ) is None:
                logger.info("Error while downloading image %s", image_url)
                return

            area, prediction_class, polygon = find_image_is_upc(
                convert_image_to_array(image).astype(np.uint8)
            )
            ImagePrediction.create(
                image=image_model,
                type="upc_image",
                model_name=MODEL_NAME,
                model_version=MODEL_VERSION,
                data={
                    "polygon": polygon,
                    "area": area,
                    "class": prediction_class.value,
                },
                max_confidence=None,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )

        # no prediction neccessary if the image is not a UPC Image
        if not prediction_class.value == "UPC_IMAGE":
            return

        prediction = Prediction(
            type=PredictionType.is_upc_image,
            value=None,
            source_image=source_image,
            server_type=product_id.server_type,
            barcode=product_id.barcode,
            automatic_processing=False,
            data={"area": area, "polygon": polygon},
            confidence=None,
            predictor=MODEL_NAME,
            predictor_version=MODEL_VERSION,
        )
        import_result = import_insights(
            [prediction], server_type=product_id.server_type
        )
        logger.info(import_result)


def run_nutriscore_object_detection(
    product_id: ProductIdentifier, image_url: str, triton_uri: str | None = None
) -> None:
    """Detect the nutriscore in an image and generate a prediction.

    :param product_id: identifier of the product
    :param image_url: URL of the image to use
    :param triton_uri: URI of the Triton Inference Server, defaults to None. If
        not provided, the default value from settings is used.
    """
    logger.info(
        "Running nutriscore object detection for %s, image %s", product_id, image_url
    )

    image = get_image_from_url(
        image_url, error_raise=False, session=http_session, use_cache=True
    )

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

        triton_uri = triton_uri or settings.TRITON_URI_NUTRISCORE
        image_prediction = run_object_detection_model(
            ObjectDetectionModel.nutriscore,
            image,
            image_model,
            triton_uri=triton_uri,
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
            predictor_version=image_prediction.model_version,
            data={"bounding_box": result["bounding_box"]},
            confidence=score,
        )
        import_result = import_insights([prediction], product_id.server_type)
        logger.info(import_result)


def run_logo_object_detection(
    product_id: ProductIdentifier,
    image_url: str,
    ocr_url: str,
    triton_uri: str | None = None,
) -> None:
    """Detect logos using the universal logo detector model and generate
    logo-related predictions.

    :param product_id: identifier of the product
    :param image_url: URL of the image to use
    :param ocr_url: URL of the OCR JSON file, used to extract text of each logo
    :param triton_uri: URI of the Triton Inference Server, defaults to None. If
        not provided, the default value from settings is used
        (settings.TRITON_URI_UNIVERSAL_LOGO_DETECTOR for the object detector model and
        settings.TRITON_URI_CLIP for the CLIP embedding model).
    """
    logger.info("Running logo object detection for %s, image %s", product_id, image_url)

    image = get_image_from_url(
        image_url, error_raise=False, session=http_session, use_cache=True
    )
    ocr_result = OCRResult.from_url(ocr_url, http_session, error_raise=False)

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
            triton_uri=triton_uri or settings.TRITON_URI_UNIVERSAL_LOGO_DETECTOR,
        )
        existing_logos = list(image_prediction.logos)

        if not existing_logos:
            logos: list[LogoAnnotation] = []
            for i, item in filter_logos(
                image_prediction.data["objects"],
                score_threshold=0.5,
                iou_threshold=0.95,
            ):
                text = None
                if ocr_result:
                    # We try to find the text in the bounding box of the logo
                    text = get_text_from_bounding_box(
                        ocr_result, item["bounding_box"], image.width, image.height
                    )
                logos.append(
                    LogoAnnotation.create(
                        image_prediction=image_prediction,
                        index=i,
                        score=item["score"],
                        bounding_box=item["bounding_box"],
                        barcode=image_model.barcode,
                        source_image=image_model.source_image,
                        text=text,
                        server_type=product_id.server_type.name,
                    )
                )
            logger.info("%s logos found for image %s", len(logos), source_image)
        else:
            # Logos already exist for this image prediction, we just make sure
            # embeddings are in DB as well
            logos = [
                existing_logo
                for existing_logo in existing_logos
                if len(list(existing_logo.embeddings)) == 0
            ]

    if logos:
        triton_stub_clip = get_triton_inference_stub(
            triton_uri or settings.TRITON_URI_CLIP
        )
        with db.connection_context():
            save_logo_embeddings(logos, image, triton_stub_clip)
        enqueue_job(
            process_created_logos,
            get_high_queue(product_id),
            job_kwargs={"result_ttl": 0},
            image_prediction_id=image_prediction.id,
            server_type=product_id.server_type,
        )


def get_text_from_bounding_box(
    ocr_result: OCRResult,
    bounding_box: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> str | None:
    """Get the text from an OCR result for a given bounding box.

    :param ocr_result: the OCR result
    :param bounding_box: the logo bounding box (in relative coordinates)
    :param image_width: the image width
    :param image_height: the image height
    :return: the text found in the bounding box, or None if no text was found
    """
    absolute_bounding_box = (
        bounding_box[0] * image_height,
        bounding_box[1] * image_width,
        bounding_box[2] * image_height,
        bounding_box[3] * image_width,
    )
    if words := ocr_result.get_words_in_area(absolute_bounding_box):
        return "".join(word.text for word in words)
    return None


def save_logo_embeddings(
    logos: list[LogoAnnotation],
    image: Image.Image,
    triton_stub: GRPCInferenceServiceStub,
):
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
    embeddings = generate_clip_embedding(resized_cropped_images, triton_stub)

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


@with_db
def add_image_fingerprint_job(image_model_id: int):
    """Job to add the fingerprint of an image in DB.

    :param image_model_id: the DB ID of the image
    """
    logger.info("Computing fingerprint for image ID %s", image_model_id)

    image_model: ImageModel
    if (image_model := ImageModel.get_or_none(id=image_model_id)) is None:
        logger.warning(
            "image ID %s not found in DB, skipping fingerprint generation",
            image_model_id,
        )
        return

    add_image_fingerprint(image_model)


@with_db
def extract_ingredients_job(
    product_id: ProductIdentifier, ocr_url: str, triton_uri: str | None = None
):
    """Extracts ingredients using ingredient extraction model from an image
    OCR.

    :param product_id: The identifier of the product to extract ingredients
        for.
    :param ocr_url: The URL of the image to extract ingredients from.
    :param triton_uri: URI of the Triton Inference Server, defaults to None. If
        not provided, the default value from settings is used
        (settings.TRITON_URI_INGREDIENT_NER).
    """
    source_image = get_source_from_url(ocr_url)

    with db:
        image_model = ImageModel.get_or_none(
            source_image=source_image, server_type=product_id.server_type.name
        )

        if not image_model:
            logger.info("Missing image in DB for image %s", source_image)
            return

        if (
            image_prediction := ImagePrediction.get_or_none(
                image=image_model, model_name=ingredient_list.MODEL_NAME
            )
        ) is not None:
            # Before the addition of the `ingredient_detection` prediction type, the
            # schema of the data field missed some important fields:
            # - `fraction_known_ingredients`: the ratio of known ingredients to
            #   total ingredients
            # - `bounding_box`: the bounding box of the ingredient list was present
            #    but was not in relative coordinates
            # As we have ~500k ingredient detections in the `image_prediction` table,
            # we don't want to rerun the model because of a schema change. Instead, we
            # convert the data to the new schema if it is not already done.
            # This function can be removed once all images are converted (we can
            # analyze the presence of the `fraction_known_ingredients` field to know
            # this).
            if "fraction_known_ingredients" not in image_prediction.data:
                image_prediction.data = convert_legacy_ingredient_image_prediction_data(
                    image_prediction.data, image_model.width, image_model.height
                )
                image_prediction.save(only=["data"])
                ingredient_prediction_data = image_prediction.data
        else:
            output = ingredient_list.predict_from_ocr(ocr_url, triton_uri=triton_uri)
            entities: list[
                ingredient_list.IngredientPredictionAggregatedEntity
            ] = output.entities  # type: ignore
            # (we know it's an aggregated entity, so we can ignore the type)

            ingredient_prediction_data = generate_ingredient_prediction_data(
                output, image_model.width, image_model.height
            )
            image_prediction = ImagePrediction.create(
                image=image_model,
                type="ner",
                model_name=ingredient_list.MODEL_NAME,
                model_version=ingredient_list.MODEL_VERSION,
                data=ingredient_prediction_data,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                max_confidence=(
                    max(entity.score for entity in entities) if entities else None
                ),
            )
            logger.info(
                "create image prediction (ingredient detection) from %s", ocr_url
            )

        if image_prediction.max_confidence is not None:
            predictions = []
            for entity in ingredient_prediction_data["entities"]:
                if "ingredients_n" not in entity:
                    logger.info("Parsing information not present in entity, skipping")
                    continue
                entity = copy.deepcopy(entity)
                value_tag = entity["lang"]["lang"]
                prediction = Prediction(
                    barcode=product_id.barcode,
                    type=PredictionType.ingredient_detection,
                    # We save the language code in the value_tag field
                    value_tag=value_tag,
                    value=None,
                    automatic_processing=False,
                    predictor=ingredient_list.MODEL_NAME,
                    predictor_version=ingredient_list.MODEL_VERSION,
                    data=entity,
                    # Use the % of recognized ingredients as the confidence score
                    confidence=entity["fraction_known_ingredients"],
                    server_type=product_id.server_type,
                    source_image=source_image,
                )
                predictions.append(prediction)

            imported = import_insights(predictions, server_type=product_id.server_type)
            logger.info(imported)


def is_valid_language_code(lang_id: str) -> bool:
    """Check if the language code is a valid 2-letter ISO-639-1 code.

    :param lang_id: The language code to validate
    :return: True if the language code is a valid 2-letter code, False otherwise
    """
    return len(lang_id) == 2 and lang_id.isalpha()


def generate_ingredient_prediction_data(
    ingredient_prediction_output: ingredient_list.IngredientPredictionOutput,
    image_width: int,
    image_height: int,
) -> JSONType:
    """Generate a JSON-like object from the ingredient prediction output to
    be saved in ImagePrediction data field.

    We remove the full text, as it's usually very long, and add a few
    additional fields:

    - `ingredients_n`: the total number of ingredients
    - `known_ingredients_n`: the number of known ingredients
    - `unknown_ingredients_n`: the number of unknown ingredients
    - `ingredients`: the parsed ingredients, in Product Opener format (with
        the `in_taxonomy` field added)

    :param ingredient_prediction_output: the ingredient prediction output
    :param image_width: the width of the image, used to convert the
        bounding box to relative coordinates
    :param image_height: the height of the image, used to convert the
        bounding box to relative coordinates
    :raises RuntimeError: if the ingredient parser fails
    :return: the generated JSON-like object
    """
    ingredient_prediction_data = dataclasses.asdict(ingredient_prediction_output)
    # Remove the full text, as it's usually very long
    ingredient_prediction_data.pop("text")
    ingredient_taxonomy = get_taxonomy(TaxonomyType.ingredient)

    for entity in ingredient_prediction_data["entities"]:
        # This is just an extra check, we should have lang information
        # available
        if entity["lang"]:
            lang_id = entity["lang"]["lang"]
            # Skip if the language code is not a valid 2-letter ISO-639-1 code.
            # Product Opener only supports ISO-639-1 codes, not ISO-639-3 codes.
            if not is_valid_language_code(lang_id):
                logger.info(
                    f"Skipping ingredient parsing for invalid language code: {lang_id}"
                )
                continue
            try:
                # Parse ingredients using Product Opener ingredient parser,
                # and add it to the entity data
                parsed_ingredients = parse_ingredients(entity["text"], lang_id)
            except RuntimeError as e:
                logger.warning(
                    "Error while parsing ingredients, skipping "
                    "to the next ingredient list",
                    exc_info=e,
                )
            else:
                ingredients_n, known_ingredients_n = add_ingredient_in_taxonomy_field(
                    parsed_ingredients, ingredient_taxonomy
                )

                # We use the same terminology as Product Opener
                entity["ingredients_n"] = ingredients_n
                entity["known_ingredients_n"] = known_ingredients_n
                entity["unknown_ingredients_n"] = ingredients_n - known_ingredients_n
                entity["ingredients"] = parsed_ingredients
                entity["fraction_known_ingredients"] = (
                    known_ingredients_n / ingredients_n if ingredients_n > 0 else 0
                )

        if entity["bounding_box"]:
            # Convert the bounding box to relative coordinates
            entity["bounding_box"] = list(
                convert_bounding_box_absolute_to_relative(
                    entity["bounding_box"],
                    width=image_width,
                    height=image_height,
                )
            )
    return ingredient_prediction_data


def convert_legacy_ingredient_image_prediction_data(
    image_prediction_data: JSONType, image_width: int, image_height: int
) -> JSONType:
    """This is a function that is temporarily used to convert the legacy
    schema for image predictions if type `ingredient_detection` to the new
    schema.

    The differences are:

    - We now have the `fraction_known_ingredients` field, which is the ratio of
        known ingredients to total ingredients
    - The bounding box is now in relative coordinates (0-1) instead of absolute
        coordinates (in pixels)

    Once all image predictions are converted, this function can be removed.

    :param image_prediction_data: the image prediction data to convert
    :param image_width: the width of the image, used to convert the
        bounding box to relative coordinates
    :param image_height: the height of the image, used to convert the
        bounding box to relative coordinates
    """
    new_data = copy.deepcopy(image_prediction_data)
    for entity in new_data["entities"]:
        # Convert the bounding box to relative coordinates
        if entity["bounding_box"]:
            entity["bounding_box"] = list(
                convert_bounding_box_absolute_to_relative(
                    entity["bounding_box"],
                    width=image_width,
                    height=image_height,
                )
            )
        # only calculate fraction_known_ingredients if the entity has ingredients data
        if "ingredients_n" in entity and "known_ingredients_n" in entity:
            entity["fraction_known_ingredients"] = (
                entity["known_ingredients_n"] / entity["ingredients_n"]
                if entity["ingredients_n"] > 0
                else 0
            )
    return new_data


def add_ingredient_in_taxonomy_field(
    parsed_ingredients: list[JSONType], ingredient_taxonomy: Taxonomy
) -> tuple[int, int]:
    """Add the `in_taxonomy` field to each ingredient in `parsed_ingredients`.

    This function is called recursively to add the `in_taxonomy` field to each
    sub-ingredient. It returns the total number of ingredients and the number
    of known ingredients (including sub-ingredients).

    :param parsed_ingredients: a list of parsed ingredients, in Product Opener
        format
    :param ingredient_taxonomy: the ingredient taxonomy
    :return: a (total_ingredients_n, known_ingredients_n) tuple
    """
    ingredients_n = 0
    known_ingredients_n = 0
    for ingredient_data in parsed_ingredients:
        ingredient_id = ingredient_data["id"]
        in_taxonomy = ingredient_id in ingredient_taxonomy
        ingredient_data["in_taxonomy"] = in_taxonomy
        known_ingredients_n += int(in_taxonomy)
        ingredients_n += 1

        if "ingredients" in ingredient_data:
            (
                sub_ingredients_n,
                known_sub_ingredients_n,
            ) = add_ingredient_in_taxonomy_field(
                ingredient_data["ingredients"], ingredient_taxonomy
            )
            ingredients_n += sub_ingredients_n
            known_ingredients_n += known_sub_ingredients_n

    return ingredients_n, known_ingredients_n


@with_db
def extract_nutrition_job(
    product_id: ProductIdentifier,
    image_url: str,
    ocr_url: str,
    triton_uri: str | None = None,
) -> None:
    """Extract nutrition information from an image OCR, and save the prediction
    in the DB.

    :param product_id: The identifier of the product to extract nutrition
        information for.
    :param image_url: The URL of the image to extract nutrition information
        from.
    :param ocr_url: The URL of the OCR JSON file
    :param triton_uri: URI of the Triton Inference Server, defaults to None. If
        not provided, the default value from settings is used.
    """
    logger.info("Running nutrition extraction for %s, image %s", product_id, image_url)
    source_image = get_source_from_url(image_url)

    with db:
        image_model = ImageModel.get_or_none(
            source_image=source_image, server_type=product_id.server_type.name
        )

        if not image_model:
            logger.info("Missing image in DB for image %s", source_image)
            return

        # Stop the job here if the image has already been processed
        if (
            ImagePrediction.get_or_none(
                image=image_model, model_name=nutrition_extraction.MODEL_NAME
            )
        ) is not None:
            return

        image = get_image_from_url(
            image_url, error_raise=False, session=http_session, use_cache=True
        )

        if image is None:
            logger.info("Error while downloading image %s", image_url)
            return

        ocr_result = OCRResult.from_url(ocr_url, http_session, error_raise=False)

        if ocr_result is None:
            logger.info("Error while downloading OCR JSON %s", ocr_url)
            return

        output = nutrition_extraction.predict(image, ocr_result, triton_uri=triton_uri)
        max_confidence = None

        if output is None:
            data: JSONType = {"error": "missing_text"}
        else:
            if output.entities.aggregated:
                max_confidence = max(
                    entity["score"] for entity in output.entities.aggregated
                )
            data = {
                "nutrients": {
                    entity: dataclasses.asdict(nutrient)
                    for entity, nutrient in output.nutrients.items()
                },
                "entities": dataclasses.asdict(output.entities),
            }
        logger.info("create image prediction (nutrition extraction) from %s", ocr_url)
        ImagePrediction.create(
            image=image_model,
            type="nutrition_extraction",
            model_name=nutrition_extraction.MODEL_NAME,
            model_version=nutrition_extraction.MODEL_VERSION,
            data=data,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            max_confidence=max_confidence,
        )

        if "nutrients" in data and len(data["nutrients"]) > 0:
            # Only keep 'postprocessed' entities, as they are the most
            # relevant for the user
            prediction_data = {
                "nutrients": data["nutrients"],
                "entities": {"postprocessed": data["entities"]["postprocessed"]},
            }
            prediction = Prediction(
                barcode=product_id.barcode,
                type=PredictionType.nutrient_extraction,
                # value and value_tag are None, all data is in data field
                value_tag=None,
                value=None,
                automatic_processing=False,
                predictor=nutrition_extraction.MODEL_NAME,
                predictor_version=nutrition_extraction.MODEL_VERSION,
                data=prediction_data,
                confidence=None,
                server_type=product_id.server_type,
                source_image=source_image,
            )
            imported = import_insights([prediction], server_type=product_id.server_type)
            logger.info(imported)
