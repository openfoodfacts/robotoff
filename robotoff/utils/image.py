import logging
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse

import numpy as np
import PIL
import requests
from PIL import Image
from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import SSLError, Timeout

from robotoff import settings

from .logger import get_logger

logger = get_logger(__name__)


def convert_image_to_array(image: Image.Image) -> np.ndarray:
    """Convert a PIL Image into a numpy array.

    The image is converted to RGB if needed before generating the array.

    :param image: the input image
    :return: the generated numpy array of shape (width, height, 3)
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    (im_width, im_height) = image.size

    return np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)


class ImageLoadingException(Exception):
    """Exception raised by `get_image_from_url`` when image cannot be fetched
    from URL or if loading failed.
    """

    pass


def get_image_from_url(
    image_url: str,
    error_raise: bool = True,
    session: Optional[requests.Session] = None,
) -> Optional[Image.Image]:
    """Fetch an image from `image_url` and load it.

    :param image_url: URL of the image to load
    :param error_raise: if True, raises a `ImageLoadingException` if an error
    occured, defaults to False. If False, None is returned if an error occurs.
    :param session: requests Session to use, by default no session is used.
    :raises ImageLoadingException: _description_
    :return: the Pillow Image or None.
    """
    auth = (
        settings._off_net_auth
        if urlparse(image_url).netloc.endswith("openfoodfacts.net")
        else None
    )
    try:
        if session:
            r = session.get(image_url, auth=auth)
        else:
            r = requests.get(image_url, auth=auth)
    except (RequestConnectionError, SSLError, Timeout) as e:
        error_message = "Cannot download image %s"
        if error_raise:
            raise ImageLoadingException(error_message % image_url) from e
        logger.info(error_message, image_url, exc_info=e)
        return None

    if not r.ok:
        error_message = "Cannot download image %s: HTTP %s"
        error_args = (image_url, r.status_code)
        if error_raise:
            raise ImageLoadingException(error_message % error_args)
        logger.log(
            logging.INFO if r.status_code < 500 else logging.WARNING,
            error_message,
            *error_args,
        )
        return None

    try:
        return Image.open(BytesIO(r.content))
    except PIL.UnidentifiedImageError:
        error_message = f"Cannot identify image {image_url}"
        if error_raise:
            raise ImageLoadingException(error_message)
        logger.info(error_message)
    except PIL.Image.DecompressionBombError:
        error_message = f"Decompression bomb error for image {image_url}"
        if error_raise:
            raise ImageLoadingException(error_message)
        logger.info(error_message)

    return None
