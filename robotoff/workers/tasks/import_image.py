import dataclasses
import datetime
from pathlib import Path
from typing import Optional

import elasticsearch
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
    Prediction,
    db,
    with_db,
)
from robotoff.off import generate_image_url, get_source_from_url, parse_ingredients
from robotoff.prediction import ingredient_list
from robotoff.prediction.upc_image import UPCImageType, find_image_is_upc
from robotoff.products import get_product_store
from robotoff.slack import NotifierFactory
from robotoff.taxonomy import get_taxonomy
from robotoff.triton import generate_clip_embedding
from robotoff.types import (
    JSONType,
    ObjectDetectionModel,
    PredictionType,
    ProductIdentifier,
    ServerType,
)
from robotoff.utils import get_image_from_url, get_logger, http_session
from robotoff.utils.image import convert_image_to_array
from robotoff.workers.queues import enqueue_job, get_high_queue, low_queue

logger = get_logger(__name__)


def run_import_image_job(product_id: ProductIdentifier, image_url: str, ocr_url: str):
    """This job is triggered every time there is a new OCR image available for
    processing by Robotoff, via /api/v1/images/import.

    On each image import, Robotoff performs the following tasks:

    1. Generates various predictions based on the OCR-extracted text from the
       image.
    2. Extracts the nutriscore prediction based on the nutriscore ML model.
    3. Triggers the 'object_detection' task
    4. Stores the imported image metadata in the Robotoff DB.
    5. Compute image fingerprint, for duplicate image detection.
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

    product_images: Optional[JSONType] = getattr(product, "images", None)
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

    # Compute image fingerprint, this job is low priority
    enqueue_job(
        add_image_fingerprint_job,
        low_queue,
        job_kwargs={"result_ttl": 0},
        image_model_id=image_model.id,
    )

    if product_id.server_type.is_food():
        # Currently we don't support insight generation for projects other
        # than OFF (OBF, OPF,...)
        enqueue_job(
            import_insights_from_image,
            get_high_queue(product_id),
            job_kwargs={"result_ttl": 0},
            product_id=product_id,
            image_url=image_url,
            ocr_url=ocr_url,
        )
        # Only extract ingredient lists for food products, as the model was not
        # trained on non-food products
        enqueue_job(
            extract_ingredients_job,
            get_high_queue(product_id),
            # We add a higher timeout, as we request Product Opener to
            # parse ingredient list, which may take a while depending on
            # the number of ingredient list (~1s per ingredient list)
            job_kwargs={"result_ttl": 0, "timeout": "2m"},
            product_id=product_id,
            ocr_url=ocr_url,
        )
    # We make sure there are no concurrent insight processing by sending
    # the job to the same queue. The queue is selected based on the product
    # barcode. See `get_high_queue` documentation for more details.
    enqueue_job(
        run_logo_object_detection,
        get_high_queue(product_id),
        job_kwargs={"result_ttl": 0},
        product_id=product_id,
        image_url=image_url,
        ocr_url=ocr_url,
    )
    enqueue_job(
        run_nutrition_table_object_detection,
        get_high_queue(product_id),
        job_kwargs={"result_ttl": 0},
        product_id=product_id,
        image_url=image_url,
    )

    # Run UPC detection to detect if the image is dominated by a UPC (and thus
    # should not be a product selected image)
    enqueue_job(
        run_upc_detection,
        get_high_queue(product_id),
        job_kwargs={"result_ttl": 0},
        product_id=product_id,
        image_url=image_url,
    )


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


def save_image_job(batch: list[tuple[ProductIdentifier, str]], server_type: ServerType):
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


def run_nutrition_table_object_detection(product_id: ProductIdentifier, image_url: str):
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
                convert_image_to_array(image)
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
                timestamp=datetime.datetime.utcnow(),
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


def run_nutriscore_object_detection(product_id: ProductIdentifier, image_url: str):
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
            predictor_version=image_prediction.model_version,
            data={"bounding_box": result["bounding_box"]},
            confidence=score,
        )
        import_result = import_insights([prediction], product_id.server_type)
        logger.info(import_result)


def run_logo_object_detection(
    product_id: ProductIdentifier, image_url: str, ocr_url: str
):
    """Detect logos using the universal logo detector model and generate
    logo-related predictions.

    :param product_id: identifier of the product
    :param image_url: URL of the image to use
    :param ocr_url: URL of the OCR JSON file, used to extract text of each logo
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
        with db.connection_context():
            save_logo_embeddings(logos, image)
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
def extract_ingredients_job(product_id: ProductIdentifier, ocr_url: str):
    """Extracts ingredients using ingredient extraction model from an image
    OCR.

    :param product_id: The identifier of the product to extract ingredients
      for.
    :param ocr_url: The URL of the image to extract ingredients from.
    """
    source_image = get_source_from_url(ocr_url)

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
                image=image_model, model_name=ingredient_list.MODEL_NAME
            )
        ) is not None:
            return

        output = ingredient_list.predict_from_ocr(ocr_url)
        entities: list[
            ingredient_list.IngredientPredictionAggregatedEntity
        ] = output.entities  # type: ignore
        # (we know it's an aggregated entity, so we can ignore the type)

        ingredient_prediction_data = generate_ingredient_prediction_data(output)
        ImagePrediction.create(
            image=image_model,
            type="ner",
            model_name=ingredient_list.MODEL_NAME,
            model_version=ingredient_list.MODEL_VERSION,
            data=ingredient_prediction_data,
            timestamp=datetime.datetime.utcnow(),
            max_confidence=max(entity.score for entity in entities)
            if entities
            else None,
        )
        logger.info("create image prediction (ingredient detection) from %s", ocr_url)


def generate_ingredient_prediction_data(
    ingredient_prediction_output: ingredient_list.IngredientPredictionOutput,
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
            try:
                # Parse ingredients using Product Opener ingredient parser,
                # and add it to the entity data
                parsed_ingredients = parse_ingredients(entity["text"], lang_id)
            except RuntimeError as e:
                logger.info(
                    "Error while parsing ingredients, skipping "
                    "to the next ingredient list",
                    exc_info=e,
                )
                continue

            ingredients_n, known_ingredients_n = add_ingredient_in_taxonomy_field(
                parsed_ingredients, ingredient_taxonomy
            )

            # We use the same terminology as Product Opener
            entity["ingredients_n"] = ingredients_n
            entity["known_ingredients_n"] = known_ingredients_n
            entity["unknown_ingredients_n"] = ingredients_n - known_ingredients_n
            entity["ingredients"] = parsed_ingredients

    return ingredient_prediction_data


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
