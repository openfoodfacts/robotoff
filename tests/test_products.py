import json
from typing import Optional

from robotoff.products import is_special_image, is_valid_image
from robotoff.settings import TEST_DATA_DIR
from robotoff.utils.types import JSONType

import pytest

with (TEST_DATA_DIR / "images.json").open("r") as f:
    IMAGE_DATA = json.load(f)


@pytest.mark.parametrize(
    "images,image_path,image_type,lang,output",
    [
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", "nutrition", None, True),
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", "nutrition", "fr", True),
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", "nutrition", "de", False),
        (IMAGE_DATA, "/303/371/006/5066/1.jpg", "nutrition", None, False),
        (IMAGE_DATA, "/303/371/006/5066/1.jpg", "nutrition", "fr", False),
        (IMAGE_DATA, "/303/371/006/5066/6.jpg", "ingredients", None, True),
        (IMAGE_DATA, "/303/371/006/5066/6.jpg", "ingredients", "fr", False),
        (IMAGE_DATA, "/303/371/006/5066/34.jpg", "ingredients", "fr", True),
    ],
)
def test_is_special_image(
    images: JSONType,
    image_path: str,
    image_type: str,
    lang: Optional[str],
    output: bool,
):
    assert is_special_image(images, image_path, image_type, lang) is output


@pytest.mark.parametrize(
    "images,image_path,output",
    [
        (IMAGE_DATA, "/303/371/006/5066/39.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/1.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/6.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/34.jpg", True),
        (IMAGE_DATA, "/303/371/006/5066/azgzg.jpg", False),
        (IMAGE_DATA, "/303/371/006/5066/nutri_plus.jpg", False),
    ],
)
def test_is_valid_image(
    images: JSONType, image_path: str, output: bool,
):
    assert is_valid_image(images, image_path) is output
