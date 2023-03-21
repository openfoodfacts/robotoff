import datetime
from pathlib import Path
from typing import Optional

from robotoff.models import ImageModel
from robotoff.off import generate_image_path, get_server_type
from robotoff.settings import BaseURLProvider
from robotoff.types import JSONType
from robotoff.utils import get_logger

logger = get_logger(__name__)


def save_image(
    barcode: str, source_image: str, images: JSONType, server_domain: str
) -> Optional[ImageModel]:
    """Save imported image details in DB.

    :param barcode: barcode of the product
    :param source_image: source image, in the format '/325/543/254/5234/1.jpg'
    :param images: image dict mapping image ID to image metadata, as returned
        by Product Opener API
    :param server_domain: the server domain to use, default to
        BaseURLProvider.server_domain()
    :return: this function return either:
        - the ImageModel of the image if it already exist in DB
        - None if the image is non raw (non-digit image ID), if it's not
          referenced in `images` or if there are no size information
        - the created ImageModel otherwise
    """
    if existing_image_model := ImageModel.get_or_none(source_image=source_image):
        logger.info(
            f"Image {source_image} already exist in DB, returning existing image"
        )
        return existing_image_model

    image_id = Path(source_image).stem

    if not image_id.isdigit():
        logger.info("Non raw image was sent: %s", source_image)
        return None

    if image_id not in images:
        logger.info("Unknown image for product %s: %s", barcode, source_image)
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


def refresh_images_in_db(
    barcode: str, images: JSONType, server_domain: Optional[str] = None
):
    """Make sure all raw images present in `images` exist in DB in image table.

    :param barcode: barcode of the product
    :param images: image dict mapping image ID to image metadata, as returned
        by Product Opener API
    :param server_domain: the server domain to use, default to
        BaseURLProvider.server_domain()
    """
    server_domain = server_domain or BaseURLProvider.server_domain()
    image_ids = [image_id for image_id in images.keys() if image_id.isdigit()]
    existing_image_ids = set(
        image_id
        for (image_id,) in ImageModel.select(ImageModel.image_id)
        .where(ImageModel.barcode == barcode, ImageModel.image_id.in_(image_ids))
        .tuples()
        .iterator()
    )
    missing_image_ids = set(image_ids) - existing_image_ids

    for missing_image_id in missing_image_ids:
        source_image = generate_image_path(barcode, missing_image_id)
        logger.debug("Creating missing image %s in DB", source_image)
        save_image(barcode, source_image, images, server_domain)
