import base64
from typing import List

import orjson
import requests

from robotoff.utils import get_logger, http_session

logger = get_logger(__name__)


def run_ocr_on_image_batch(base64_images: List[str], api_key: str) -> requests.Response:
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    return http_session.post(
        url,
        json={
            "requests": [
                {
                    "features": [
                        {"type": "TEXT_DETECTION"},
                        {"type": "FACE_DETECTION"},
                        {"type": "LABEL_DETECTION"},
                        {"type": "SAFE_SEARCH_DETECTION"},
                    ],
                    "image": {"content": base64_image},
                }
                for base64_image in base64_images
            ]
        },
    )


def run_ocr_on_image(image_bytes: bytes, api_key: str):
    if not image_bytes:
        raise ValueError("empty image")

    content = base64.b64encode(image_bytes).decode("utf-8")
    r = run_ocr_on_image_batch([content], api_key)

    if not r.ok:
        logger.info("HTTP %s received", r.status_code)
        logger.info("Response: %s", r.text)
        return
    return orjson.loads(r.content)
