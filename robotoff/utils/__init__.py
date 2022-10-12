import gzip
import logging
import os
import pathlib
import sys
from io import BytesIO
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import orjson
import PIL
import requests
from PIL import Image

from robotoff import settings


def get_logger(name=None, level: Optional[int] = None):
    logger = logging.getLogger(name)

    if level is None:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = logging.getLevelName(log_level)

        if not isinstance(level, int):
            print(
                "Unknown log level: {}, fallback to INFO".format(log_level),
                file=sys.stderr,
            )
            level = 20

    logger.setLevel(level)

    if name is None:
        configure_root_logger(logger, level)

    return logger


def configure_root_logger(logger, level: int = 20):
    logger.setLevel(level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s :: %(processName)s :: "
        "%(threadName)s :: %(levelname)s :: "
        "%(message)s"
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)


logger = get_logger(__name__)


def jsonl_iter(jsonl_path: Union[str, pathlib.Path]) -> Iterable[Dict]:
    open_fn = get_open_fn(jsonl_path)

    with open_fn(str(jsonl_path), "rt", encoding="utf-8") as f:
        yield from jsonl_iter_fp(f)


def gzip_jsonl_iter(jsonl_path: Union[str, pathlib.Path]) -> Iterable[Dict]:
    with gzip.open(jsonl_path, "rt", encoding="utf-8") as f:
        yield from jsonl_iter_fp(f)


def jsonl_iter_fp(fp) -> Iterable[Dict]:
    for line in fp:
        line = line.strip("\n")
        if line:
            yield orjson.loads(line)


def load_json(
    path: Union[str, pathlib.Path], compressed: bool = False
) -> Union[Dict, List]:
    """Load a JSON file.

    :param path: the path of the file
    :param: compressed: if True, use gzip to decompress the file
    :return: the unserialized JSON
    """
    if compressed:
        with gzip.open(str(path), "rb") as f:
            return orjson.loads(f.read())
    else:
        with open(str(path), "rb") as f:
            return orjson.loads(f.read())


def dump_json(path: Union[str, pathlib.Path], item: Any, compressed: bool = False):
    """Dump an object in a JSON file.

    :param path: the path of the file
    :param item: the item to serialize
    :param: compressed: if True, use gzip to compress the file
    """
    if compressed:
        with gzip.open(str(path), "wb") as f:
            f.write(orjson.dumps(item))
    else:
        with open(str(path), "wb") as f:
            f.write(orjson.dumps(item))


def dump_jsonl(
    filepath: Union[str, pathlib.Path],
    json_iter: Iterable[Any],
) -> int:
    count = 0
    open_fn = get_open_fn(filepath)

    with open_fn(str(filepath), "wb") as f:
        for item in json_iter:
            f.write(orjson.dumps(item) + b"\n")
            count += 1

    return count


def get_open_fn(filepath: Union[str, pathlib.Path]) -> Callable:
    filepath = str(filepath)
    if filepath.endswith(".gz"):
        return gzip.open
    else:
        return open


def text_file_iter(
    filepath: Union[str, pathlib.Path], comment: bool = True
) -> Iterable[str]:
    open_fn = get_open_fn(filepath)

    with open_fn(str(filepath), "rt") as f:
        for item in f:
            item = item.strip("\n")

            if item:
                # commented lines start with '//'
                if not comment or not item.startswith("//"):
                    yield item


def dump_text(filepath: Union[str, pathlib.Path], text_iter: Iterable[str]):
    with open(str(filepath), "w") as f:
        for item in text_iter:
            item = item.strip("\n")
            f.write(item + "\n")


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
    if session:
        r = session.get(image_url)
    else:
        r = requests.get(image_url)

    if not r.ok:
        error_message = f"Cannot load image {image_url}: HTTP {r.status_code}"
        if error_raise:
            raise ImageLoadingException(error_message)
        logger.warning(error_message)
        return None

    try:
        return Image.open(BytesIO(r.content))
    except PIL.UnidentifiedImageError:
        error_message = f"Cannot identify image {image_url}"
        if error_raise:
            raise ImageLoadingException(error_message)
        logger.warning(error_message)
    except PIL.Image.DecompressionBombError:
        error_message = f"Decompression bomb error for image {image_url}"
        if error_raise:
            raise ImageLoadingException(error_message)
        logger.warning(error_message)

    return None


http_session = requests.Session()
USER_AGENT_HEADERS = {
    "User-Agent": settings.ROBOTOFF_USER_AGENT,
}
http_session.headers.update(USER_AGENT_HEADERS)
