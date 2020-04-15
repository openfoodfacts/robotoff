import gzip
import json
import logging
import os
import pathlib
import tempfile

import requests
import sys
from typing import Callable, Union, Iterable, Dict, Optional

from PIL import Image


def get_logger(name=None, level: str = "INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if name is None:
        configure_root_logger(logger, level)

    return logger


def configure_root_logger(logger, level: str = "INFO"):
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "FATAL", "CRITICAL"):
        print(
            "Unknown log level: {}, fallback " "to INFO".format(log_level),
            file=sys.stderr,
        )
        log_level = level

    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s :: %(processName)s :: "
        "%(threadName)s :: %(levelname)s :: "
        "%(message)s"
    )
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
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


def dump_jsonl(filepath: Union[str, pathlib.Path], json_iter: Iterable[Dict]) -> int:
    count = 0
    open_fn = get_open_fn(filepath)

    with open_fn(str(filepath), "wt") as f:
        for item in json_iter:
            f.write(json.dumps(item) + "\n")
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
