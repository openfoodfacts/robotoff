import datetime
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image

from robotoff.elasticsearch import get_es_client
from robotoff.logos import delete_ann_logos
from robotoff.models import (
    ImageModel,
    ImagePrediction,
    LogoAnnotation,
    LogoEmbedding,
    Prediction,
    ProductInsight,
)
from robotoff.off import generate_image_path, generate_image_url
from robotoff.types import JSONType, ProductIdentifier
from robotoff.utils import get_image_from_url, get_logger, http_session

logger = get_logger(__name__)


def save_image(
    product_id: ProductIdentifier,
    source_image: str,
    image_url: str,
    images: JSONType | None,
    use_cache: bool = False,
) -> ImageModel | None:
    """Save imported image details in DB.

    :param product_id: identifier of the product
    :param source_image: source image, in the format '/325/543/254/5234/1.jpg'
    :param image_url: URL of the image, only used to get image size if images
        is None
    :param images: image dict mapping image ID to image metadata, as returned
        by Product Opener API, is None if MongoDB access is disabled
        (`ENABLE_MONGODB_ACCESS=False`)
    :return: this function return either:
        - the ImageModel of the image if it already exist in DB
        - None if the image is non raw (non-digit image ID), if it's not
          referenced in `images` or if there are no size information
        - the created ImageModel otherwise
    """
    if existing_image_model := ImageModel.get_or_none(
        source_image=source_image, server_type=product_id.server_type.name
    ):
        logger.info(
            "Image %s already exist in DB, returning existing image", source_image
        )
        return existing_image_model

    image_id = Path(source_image).stem

    if not image_id.isdigit():
        logger.info("Non raw image was sent: %s", source_image)
        return None

    if images is not None:
        if image_id not in images:
            logger.info("Unknown image for %s: %s", product_id, source_image)
            return None

        image = images[image_id]
        sizes = image.get("sizes", {}).get("full")

        if not sizes:
            logger.info("Image with missing size information: %s", image)
            # width and height are non-null fields, so provide default values
            return None

        width = sizes["w"]
        height = sizes["h"]
        uploaded_t = image.get("uploaded_t")
        if not uploaded_t:
            logger.info("Missing uploaded_t information: %s", list(image))

        elif isinstance(uploaded_t, str) and not uploaded_t.isdigit():
            logger.info("Non digit uploaded_t value: %s", uploaded_t)
            uploaded_t = None
        else:
            uploaded_t = int(uploaded_t)

        if uploaded_t is not None:
            uploaded_at = datetime.datetime.fromtimestamp(
                uploaded_t, datetime.timezone.utc
            )
    else:
        uploaded_at = None
        # DB product check is disabled which means we shouldn't rely on having
        # a MongoDB instance running. As image size information is stored in
        # MongoDB (in the `images` field), we download the image to know the
        # image size
        logger.info("DB Product check disabled, downloading image to get image size")
        image = get_image_from_url(
            image_url, error_raise=False, session=http_session, use_cache=use_cache
        )

        if image is None:
            logger.info("Could not import image %s in DB", image_url)
            return None

        width = image.width
        height = image.height

    image_model = ImageModel.create(
        barcode=product_id.barcode,
        image_id=image_id,
        width=width,
        height=height,
        source_image=source_image,
        uploaded_at=uploaded_at,
        server_type=product_id.server_type.name,
    )
    if image_model is not None:
        logger.info("New image %s created in DB", image_model.id)
    return image_model


def refresh_images_in_db(product_id: ProductIdentifier, images: JSONType):
    """Make sure all raw images present in `images` exist in DB in image table.

    :param product_id: identifier of the product
    :param images: image dict mapping image ID to image metadata, as returned
        by Product Opener API
    """
    image_ids = [image_id for image_id in images.keys() if image_id.isdigit()]
    existing_image_ids = set(
        image_id
        for (image_id,) in ImageModel.select(ImageModel.image_id)
        .where(
            ImageModel.barcode == product_id.barcode,
            ImageModel.server_type == product_id.server_type.name,
            ImageModel.image_id.in_(image_ids),
        )
        .tuples()
        .iterator()
    )
    missing_image_ids = set(image_ids) - existing_image_ids

    for missing_image_id in missing_image_ids:
        source_image = generate_image_path(product_id, missing_image_id)
        image_url = generate_image_url(product_id, missing_image_id)
        logger.debug("Creating missing image %s in DB", source_image)
        save_image(product_id, source_image, image_url, images, use_cache=True)


def add_image_fingerprint(image_model: ImageModel, overwrite: bool = False) -> None:
    """Update image in DB to add the image fingerprint.

    :param image_model: the image model to update
    :param overwrite: whether to overwrite the existing fingerprint
    """
    if not overwrite and image_model.fingerprint is not None:
        logger.debug("image %s already has a fingerprint, skipping", image_model.id)
        return

    image_url = image_model.get_image_url()
    image = get_image_from_url(
        image_url, error_raise=False, session=http_session, use_cache=True
    )

    if image is None:
        logger.info(
            "could not fetch image from %s, aborting image fingerprinting", image_url
        )
        return

    image_model.fingerprint = generate_image_fingerprint(image)
    ImageModel.bulk_update([image_model], fields=["fingerprint"])


def generate_image_fingerprint(image: Image.Image) -> int:
    """Generate a fingerprint from an image, used for near-duplicate
    detection.

    We use perceptual hashing algorithm.

    :param image: the input image
    :return: the fingerprint, as a 64-bit integer
    """
    array = imagehash.phash(image).hash
    # `int_array` is a flattened int array of dim 64
    int_array = array.flatten().astype(int)
    # convert the 64-bit array to a 64 bits integer
    fingerprint = int_array.dot(2 ** np.arange(int_array.size)[::-1])
    return fingerprint


def delete_images(product_id: ProductIdentifier, image_ids: list[str]):
    """Delete images and related items in DB.

    This function must be called when Robotoff gets notified of an image
    deletion. It proceeds as follow:

    - mark the image as `deleted` in the `image` table
    - delete all predictions associated with the image (`prediction` table)
    - delete all non-annotated insights associated with the image
      (`product_insight` table). Annotated insights are kept for reference.

    :param product_id: identifier of the product
    :param image_ids: a list of image IDs to delete.
      Each image ID must be a digit.
    """

    if not product_id.is_valid():
        logger.warning("Could not delete images, invalid product identifier")
        return

    server_type = product_id.server_type.name
    # Perform batching as we don't know the number of images to delete
    updated_models = []
    source_images = []
    deleted_embeddings_total = 0
    deleted_logos_total = 0
    es_client = get_es_client()
    for image_id in image_ids:
        source_image = generate_image_path(product_id, image_id)
        image_model = ImageModel.get_or_none(
            source_image=source_image, server_type=server_type
        )

        if image_model is None:
            logger.info(
                "image to delete %s for product %s not found in DB, skipping",
                image_id,
                product_id,
            )
            continue

        # set the `deleted` flag to True: image models are always kept in DB
        image_model.deleted = True
        updated_models.append(image_model)
        source_images.append(source_image)

        # Fetch all logos associated with the image to delete
        logos = list(
            LogoAnnotation.select(LogoAnnotation.id)
            .join(ImagePrediction)
            .where(ImagePrediction.image == image_model)
        )
        # Delete the logos from ES
        logo_ids = [logo.id for logo in logos]
        delete_ann_logos(es_client, logo_ids)
        # delete the embeddings associated with the logos in DB
        deleted_embeddings_total += (
            LogoEmbedding.delete().where(LogoEmbedding.logo_id.in_(logo_ids)).execute()
        )
        deleted_logos = (
            LogoAnnotation.delete()
            .where(
                LogoAnnotation.id.in_(logo_ids),
                # Only delete logos that are not annotated
                LogoAnnotation.completed_at.is_null(True),
            )
            .execute()
        )
        deleted_logos_total += deleted_logos

        if deleted_logos == len(logo_ids):
            # All logos were deleted, delete the image prediction
            ImagePrediction.delete().where(
                ImagePrediction.image == image_model
            ).execute()

    updated_image_models: int = (
        ImageModel.bulk_update(updated_models, fields=["deleted"])
        if updated_models
        else 0
    )
    deleted_predictions: int = (
        Prediction.delete()
        .where(
            Prediction.source_image.in_(source_images),
            Prediction.server_type == server_type,
            # Add barcode filter to speed up the query
            Prediction.barcode == product_id.barcode,
        )
        .execute()
    )
    deleted_insights: int = (
        ProductInsight.delete()
        .where(
            ProductInsight.source_image.in_(source_images),
            ProductInsight.server_type == server_type,
            ProductInsight.annotation.is_null(),
            # Add barcode filter to speed up the query
            ProductInsight.barcode == product_id.barcode,
        )
        .execute()
    )

    logger.info(
        "deleted %s image in DB, %s deleted predictions, %s deleted insights, "
        "%s deleted embeddings, %s deleted logos",
        updated_image_models,
        deleted_predictions,
        deleted_insights,
        deleted_embeddings_total,
        deleted_logos_total,
    )
