from io import BytesIO

import numpy as np
import PIL
import requests
from PIL import Image

from robotoff.utils.download import (
    AssetLoadingException,
    cache_asset_from_url,
    get_asset_from_url,
)

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


def get_image_from_url(
    image_url: str,
    error_raise: bool = True,
    session: requests.Session | None = None,
    use_cache: bool = False,
    cache_expire: int = 86400,
) -> Image.Image | None:
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
    :return: the Pillow Image or None.
    """
    if use_cache:
        content_bytes = cache_asset_from_url(
            key=f"image:{image_url}",
            cache_expire=cache_expire,
            tag="image",
            # kwargs passed to get_asset_from_url
            image_url=image_url,
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

    return None
