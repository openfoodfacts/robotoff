import datetime
from pathlib import Path
from typing import Optional

from robotoff.models import ImageModel
from robotoff.off import generate_image_path, generate_image_url
from robotoff.types import JSONType, ProductIdentifier
from robotoff.utils import get_image_from_url, get_logger, http_session

logger = get_logger(__name__)


def save_image(
    product_id: ProductIdentifier,
    source_image: str,
    image_url: str,
    images: Optional[JSONType],
) -> Optional[ImageModel]:
    """Save imported image details in DB.

    :param product_id: identifier of the product
    :param source_image: source image, in the format '/325/543/254/5234/1.jpg'
    :param image_url: URL of the image, only used to get image size if images
        is None
    :param images: image dict mapping image ID to image metadata, as returned
        by Product Opener API, is None if product validity check is disabled
        (`ENABLE_PRODUCT_CHECK=False`)
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
            f"Image {source_image} already exist in DB, returning existing image"
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
            uploaded_at = datetime.datetime.utcfromtimestamp(uploaded_t)
    else:
        uploaded_at = None
        # DB product check is disabled which means we shouldn't rely on having
        # a MongoDB instance running. As image size information is stored in
        # MongoDB (in the `images` field), we download the image to know the image
        # size
        logger.info("DB Product check disabled, downloading image to get image size")
        image = get_image_from_url(image_url, error_raise=False, session=http_session)

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
        source_image = generate_image_path(product_id.barcode, missing_image_id)
        image_url = generate_image_url(product_id, missing_image_id)
        logger.debug("Creating missing image %s in DB", source_image)
        save_image(product_id, source_image, image_url, images)
