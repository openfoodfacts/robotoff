import gzip
import pathlib
from typing import Any, Callable, Iterable, Union

import orjson
import requests
from requests.adapters import HTTPAdapter

from robotoff import settings
from robotoff.types import JSONType

from .image import get_image_from_url  # noqa: F401
from .logger import get_logger

logger = get_logger(__name__)


def jsonl_iter(jsonl_path: Union[str, pathlib.Path]) -> Iterable[JSONType]:
    """Iterate over elements of a JSONL file.

    :param jsonl_path: the path of the JSONL file. Both plain (.jsonl) and
        gzipped (jsonl.gz) files are supported.
    :yield: dict contained in the JSONL file
    """
    open_fn = get_open_fn(jsonl_path)

    with open_fn(str(jsonl_path), "rt", encoding="utf-8") as f:
        yield from jsonl_iter_fp(f)


def gzip_jsonl_iter(jsonl_path: Union[str, pathlib.Path]) -> Iterable[dict]:
    with gzip.open(jsonl_path, "rt", encoding="utf-8") as f:
        yield from jsonl_iter_fp(f)


def jsonl_iter_fp(fp) -> Iterable[dict]:
    for line in fp:
        line = line.strip("\n")
        if line:
            yield orjson.loads(line)


def load_json(
    path: Union[str, pathlib.Path], compressed: bool = False
) -> Union[dict, list]:
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
    open_fn = get_open_fn(filepath)

    with open_fn(str(filepath), "wt") as f:
        for item in text_iter:
            item = item.strip("\n")
            f.write(item + "\n")


http_session = requests.Session()
USER_AGENT_HEADERS = {
    "User-Agent": settings.ROBOTOFF_USER_AGENT,
}
http_session.headers.update(USER_AGENT_HEADERS)
static_adapter = HTTPAdapter(max_retries=3)
http_session.mount("https://static.openfoodfacts.", static_adapter)
http_session.mount("https://images.openfoodfacts.", static_adapter)
