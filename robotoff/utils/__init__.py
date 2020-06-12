import datetime
import gzip
import json
import logging
import os
import pathlib
import sys
import tempfile
from typing import Callable, Dict, Iterable, Optional, Type, Union
import uuid

from PIL import Image
import requests

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
            yield json.loads(line)


def dump_jsonl(
    filepath: Union[str, pathlib.Path],
    json_iter: Iterable[Dict],
    serializer: Optional[Type] = None,
) -> int:
    count = 0
    open_fn = get_open_fn(filepath)

    with open_fn(str(filepath), "wt") as f:
        for item in json_iter:
            f.write(json.dumps(item, cls=serializer) + "\n")
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


def get_image_from_url(
    image_url: str,
    error_raise: bool = False,
    session: Optional[requests.Session] = None,
) -> Optional[Image.Image]:
    if session:
        r = session.get(image_url)
    else:
        r = requests.get(image_url)

    if error_raise:
        r.raise_for_status()

    if r.status_code != 200:
        return None

    with tempfile.NamedTemporaryFile() as f:
        f.write(r.content)
        image = Image.open(f.name)

    return image


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)


http_session = requests.Session()
USER_AGENT_HEADERS = {
    "User-Agent": settings.ROBOTOFF_USER_AGENT,
}
http_session.headers.update(USER_AGENT_HEADERS)
