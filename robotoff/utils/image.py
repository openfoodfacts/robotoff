import logging
from io import BytesIO
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import PIL
import requests
from PIL import Image

from robotoff.types import JSONType
from robotoff.utils.download import (
    AssetLoadingException,
    cache_asset_from_url,
    get_asset_from_url,
)

logger = logging.getLogger(__name__)


def convert_image_to_array(image: Image.Image) -> np.ndarray:
    """Convert a PIL Image into a numpy array.

    The image is converted to RGB if needed before generating the array.

    :param image: the input image.
    :return: the generated numpy array of shape (width, height, 3)
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    (im_width, im_height) = image.size

    return np.array(image.getdata()).reshape((im_height, im_width, 3))


def get_image_from_url(
    image_url: str,
    error_raise: bool = True,
    session: requests.Session | None = None,
    use_cache: bool = False,
    cache_expire: int = 86400,
    return_type: Literal["PIL", "np", "bytes"] = "PIL",
) -> Image.Image | np.ndarray | bytes | None:
    """Fetch an image from `image_url` and load it.

    :param image_url: URL of the image to load
    :param error_raise: if True, raises a `AssetLoadingException` if an error
      occured, defaults to False. If False, None is returned if an error
      occured.
    :param session: requests Session to use, by default no session is used.
    :param use_cache: if True, we use the local file cache (and save the
      result in the cache in case of cache miss)
    :param cache_expire: the expiration value of the item in the cache (in
      seconds), default to 86400 (24h).
    :param return_type: the type of object to return, can be "PIL" (Pillow
      Image), "np" (numpy array) or "bytes" (raw bytes). Defaults to "PIL".
    :return: the Pillow Image or None.
    """
    if return_type not in ("PIL", "np", "bytes"):
        raise ValueError(f"Invalid return_type {return_type}")

    if use_cache:
        content_bytes = cache_asset_from_url(
            key=f"image:{image_url}",
            cache_expire=cache_expire,
            tag="image",
            # kwargs passed to get_asset_from_url
            asset_url=image_url,
            error_raise=error_raise,
            session=session,
        )
        if content_bytes is None:
            return None
    else:
        r = get_asset_from_url(image_url, error_raise, session)
        if r is None:
            return None
        content_bytes = r.content

    if return_type == "PIL":
        try:
            return Image.open(BytesIO(content_bytes))
        except PIL.UnidentifiedImageError:
            error_message = f"Cannot identify image {image_url}"
            if error_raise:
                raise AssetLoadingException(error_message)
            logger.info(error_message)
        except PIL.Image.DecompressionBombError:
            error_message = f"Decompression bomb error for image {image_url}"
            if error_raise:
                raise AssetLoadingException(error_message)
            logger.info(error_message)

    elif return_type == "np":
        try:
            image = cv2.imdecode(
                np.frombuffer(content_bytes, dtype=np.uint8), cv2.IMREAD_COLOR_RGB
            )
            if image is None:
                raise ValueError("cv2.imdecode could not decode image")
            return image
        except Exception as e:
            error_message = f"Error decoding image {image_url}: {e}"
            if error_raise:
                raise AssetLoadingException(error_message)
            logger.info(error_message)

    elif return_type == "bytes":
        return content_bytes

    return None


def convert_bounding_box_absolute_to_relative_from_images(
    bounding_box_absolute: tuple[int, int, int, int],
    images: JSONType,
    source_image: str | None,
) -> tuple[float, float, float, float] | None:
    """Convert absolute bounding box coordinates to relative ones.

    When detecting patterns using regex or flashtext, we don't know the size of
    the image, so we cannot compute the relative coordinates of the text
    bounding box. We perform the conversion during insight import instead.

    Relative coordinates are used as they are more convenient than absolute
    ones (we can use them on a resized version of the original image).

    :param bounding_box_absolute: absolute coordinates of the bounding box
    :param images: The image dict as stored in MongoDB.
    :param source_image: The insight source image, should be the path of the
    image path or None.
    :return: a (y_min, x_min, y_max, x_max) tuple of the relative coordinates
        or None if a conversion error occured
    """
    if source_image is None:
        logger.warning(
            "could not convert absolute coordinate bounding box: "
            "bounding box was provided (%s) but source image is null",
            bounding_box_absolute,
        )
        return None

    image_id = Path(source_image).stem

    if image_id not in images:
        logger.info(
            "could not convert absolute coordinate bounding box: "
            "image %s not found in product images",
            image_id,
        )
        return None

    size = images[image_id]["sizes"]["full"]
    return convert_bounding_box_absolute_to_relative(
        bounding_box_absolute, size["w"], size["h"]
    )


def convert_bounding_box_absolute_to_relative(
    bounding_box_absolute: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    """Convert absolute bounding box coordinates to relative ones.

    :param bounding_box_absolute: absolute coordinates of the bounding box.
        The coordinates are in the format (y_min, x_min, y_max, x_max)
    :param width: The width of the image
    :param height: The height of the image
    :return: a (y_min, x_min, y_max, x_max) tuple of the relative coordinates
    """
    return (
        max(0.0, bounding_box_absolute[0] / height),
        max(0.0, bounding_box_absolute[1] / width),
        min(1.0, bounding_box_absolute[2] / height),
        min(1.0, bounding_box_absolute[3] / width),
    )
