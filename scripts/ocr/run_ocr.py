#!/usr/bin/python3
"""Script to generate missing or corrupted Google Cloud Vision JSON.

To run, simply run as root, with the Google API_KEY as envvar:
`CLOUD_VISION_API_KEY='{KEY}' python3 run_ocr.py`

Missing JSON will be added, and corrupted JSON or Google Cloud Vision JSON
containing an 'errors' fields will be replaced.
"""

import argparse
import base64
import glob
import gzip
import os
import pathlib
import sys
import time
from datetime import datetime
from typing import List, Optional

import orjson
import requests

API_KEY = os.environ.get("CLOUD_VISION_API_KEY")
MAXIMUM_MODIFICATION_DATETIME = datetime(year=2019, month=5, day=1)

if not API_KEY:
    sys.exit("missing Google Cloud CLOUD_VISION_API_KEY as envvar")


CLOUD_VISION_URL = "https://vision.googleapis.com/v1/images:annotate?key={}".format(
    API_KEY
)

BASE_IMAGE_DIR = pathlib.Path("/srv2/off/html/images/products")
session = requests.Session()


def get_base64_image_from_url(
    image_url: str,
    error_raise: bool = False,
    session: Optional[requests.Session] = None,
) -> Optional[str]:
    if session:
        r = session.get(image_url)
    else:
        r = requests.get(image_url)

    if error_raise:
        r.raise_for_status()

    if r.status_code != 200:
        return None

    return base64.b64encode(r.content).decode("utf-8")


def get_base64_image_from_path(
    image_path: pathlib.Path,
    error_raise: bool = False,
) -> Optional[str]:
    try:
        with image_path.open("rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        if error_raise:
            raise e
        else:
            print(e)
            return None


def run_ocr_on_image_batch(base64_images: List[str]) -> requests.Response:
    r = session.post(
        CLOUD_VISION_URL,
        json={
            "requests": [
                {
                    "features": [
                        {"type": "TEXT_DETECTION"},
                        {"type": "LOGO_DETECTION"},
                        {"type": "LABEL_DETECTION"},
                        {"type": "SAFE_SEARCH_DETECTION"},
                        {"type": "FACE_DETECTION"},
                    ],
                    "image": {"content": base64_image},
                }
                for base64_image in base64_images
            ]
        },
    )
    return r


def run_ocr_on_image_paths(image_paths: List[pathlib.Path], override: bool = False):
    images_content = []
    for image_path in image_paths:
        json_path = image_path.with_suffix(".json.gz")
        if json_path.is_file():
            if override:
                # print("Deleting file {}".format(json_path))
                json_path.unlink()
            else:
                continue

        content = get_base64_image_from_path(image_path)

        if content:
            images_content.append((image_path, content))

    if not images_content:
        return [], False

    r = run_ocr_on_image_batch([x[1] for x in images_content])

    if not r.ok:
        print("HTTP {} received".format(r.status_code))
        print("Response: {}".format(r.text))
        print(image_paths)
        return [], True

    r_json = orjson.loads(r.content)
    responses = r_json["responses"]
    return (
        [(images_content[i][0], responses[i]) for i in range(len(images_content))],
        True,
    )


def dump_ocr(
    image_paths: List[pathlib.Path], sleep: float = 0.0, override: bool = False
):
    responses, performed_request = run_ocr_on_image_paths(image_paths, override)

    for image_path, response in responses:
        json_path = image_path.with_suffix(".json.gz")

        with gzip.open(str(json_path), "wb") as f:
            # print("Dumping OCR JSON to {}".format(json_path))
            f.write(orjson.dumps({"responses": [response]}))

    if performed_request and sleep:
        time.sleep(sleep)


def add_to_seen_set(seen_path: pathlib.Path, item: str):
    with seen_path.open("a", encoding="utf-8") as f:
        f.write("{}\n".format(item))


def add_missing_ocr(sleep: float, seen_path: pathlib.Path):
    total = 0
    missing = 0
    json_error = 0
    ocr_error = 0
    valid = 0
    empty_images = 0
    expired = 0

    with seen_path.open("r", encoding="utf-8") as f:
        seen_set = set(map(str.strip, f))

    for i, image_path_str in enumerate(
        glob.iglob("{}/**/*.jpg".format(BASE_IMAGE_DIR))
    ):
        if i % 10000 == 0:
            print(
                "scanned: {}, total: {}, missing: {}, json_error: {}, ocr_error: {}, empty images: {}, valid: {}, "
                "expired: {}".format(
                    i,
                    total,
                    missing,
                    json_error,
                    ocr_error,
                    empty_images,
                    valid,
                    expired,
                )
            )

        image_path = pathlib.Path(image_path_str)
        if not image_path.stem.isdigit():
            continue

        if image_path_str in seen_set:
            continue

        image_size = image_path.stat().st_size

        if not image_size:
            empty_images += 1
            add_to_seen_set(seen_path, image_path_str)
            continue

        if image_size >= 10485760:
            add_to_seen_set(seen_path, image_path_str)
            continue

        json_path = image_path.with_suffix(".json.gz")
        total += 1

        if not json_path.is_file():
            plain_json_path = image_path.with_suffix(".json")
            if plain_json_path.is_file():
                continue

            missing += 1
            dump_ocr([image_path], sleep=sleep, override=False)
            add_to_seen_set(seen_path, image_path_str)
            continue

        modification_datetime = datetime.fromtimestamp(json_path.stat().st_mtime)
        if modification_datetime < MAXIMUM_MODIFICATION_DATETIME:
            expired += 1
            dump_ocr([image_path], sleep=sleep, override=True)
            add_to_seen_set(seen_path, image_path_str)
            continue

        has_json_error = False
        with gzip.open(str(json_path), "rb") as f:
            try:
                data = orjson.loads(f.read())
            except orjson.JSONDecodeError:
                has_json_error = True

        if has_json_error:
            json_error += 1
            dump_ocr([image_path], sleep=sleep, override=True)
            add_to_seen_set(seen_path, image_path_str)
            continue

        has_error = False
        for response in data["responses"]:
            if "error" in response:
                has_error = True

        if has_error:
            ocr_error += 1
            dump_ocr([image_path], sleep=sleep, override=True)
            add_to_seen_set(seen_path, image_path_str)
        else:
            valid += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--seen-path", type=pathlib.Path, required=True)
    args = parser.parse_args()
    add_missing_ocr(sleep=args.sleep, seen_path=args.seen_path)
