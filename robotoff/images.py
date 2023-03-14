import datetime
from pathlib import Path
from typing import Optional

from robotoff.models import ImageModel
from robotoff.off import get_server_type
from robotoff.types import JSONType
from robotoff.utils import get_logger

logger = get_logger(__name__)


def save_image(
    barcode: str, source_image: str, images: JSONType, server_domain: str
) -> Optional[ImageModel]:
    """Save imported image details in DB."""
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
