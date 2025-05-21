import json
from typing import Optional
from unittest.mock import MagicMock

import pytest

from robotoff.products import DBProductStore, is_special_image, is_valid_image
from robotoff.settings import TEST_DATA_DIR
from robotoff.types import JSONType, ProductIdentifier, ServerType

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
    images: JSONType,
    image_path: str,
    output: bool,
):
    assert is_valid_image(images, image_path) is output


IMAGES_WITH_LEGACY_SCHEMA = {
    "1": {
        "sizes": {
            "100": {"h": 100, "w": 56},
            "400": {"h": 400, "w": 225},
            "full": {"h": 3555, "w": 2000},
        },
        "uploaded_t": "1490702616",
        "uploader": "user1",
    },
    "nutrition_fr": {
        "angle": None,
        "geometry": "0x0-0-0",
        "imgid": "1",
        "normalize": "0",
        "ocr": 1,
        "orientation": "0",
        "rev": "18",
        "sizes": {
            "100": {"h": 53, "w": 100},
            "200": {"h": 107, "w": 200},
            "400": {"h": 213, "w": 400},
            "full": {"h": 1093, "w": 2050},
        },
        "white_magic": "0",
        "x1": None,
        "x2": None,
        "y1": None,
        "y2": None,
    },
}


IMAGES_WITH_NEW_SCHEMA = {
    "uploaded": {
        "1": {
            "sizes": {
                "100": {
                    "h": 100,
                    "w": 56,
                    "url": "https://images.openfoodfacts.org/images/products/326/385/950/6216/1.100.jpg",
                },
                "400": {
                    "h": 400,
                    "w": 225,
                    "url": "https://images.openfoodfacts.org/images/products/326/385/950/6216/1.400.jpg",
                },
                "full": {
                    "h": 3555,
                    "w": 2000,
                    "url": "https://images.openfoodfacts.org/images/products/326/385/950/6216/1.jpg",
                },
            },
            "uploaded_t": "1490702616",
            "uploader": "user1",
        },
    },
    "selected": {
        "nutrition": {
            "fr": {
                "imgid": "1",
                "rev": "18",
                "sizes": {
                    "100": {
                        "h": 53,
                        "w": 100,
                        "url": "https://images.openfoodfacts.org/images/products/326/385/950/6216/nutrition_fr.18.100.jpg",
                    },
                    "200": {
                        "h": 107,
                        "w": 200,
                        "url": "https://images.openfoodfacts.org/images/products/326/385/950/6216/nutrition_fr.18.200.jpg",
                    },
                    "400": {
                        "h": 213,
                        "w": 400,
                        "url": "https://images.openfoodfacts.org/images/products/326/385/950/6216/nutrition_fr.18.400.jpg",
                    },
                    "full": {
                        "h": 1093,
                        "w": 2050,
                        "url": "https://images.openfoodfacts.org/images/products/326/385/950/6216/nutrition_fr.18.full.jpg",
                    },
                },
                "generation": {
                    "white_magic": "0",
                    "x1": None,
                    "x2": None,
                    "y1": None,
                    "y2": None,
                    "normalize": "0",
                    "ocr": 1,
                    "orientation": "0",
                    "angle": None,
                    "geometry": "0x0-0-0",
                },
            },
        }
    },
}


class TestDBProductStore:
    @pytest.mark.parametrize(
        "barcode,projection,db_output,expected_output",
        [
            (
                "1234567890",
                None,
                {
                    "_id": "1234567890",
                    "code": "1234567890",
                    "product_name": "Fusilli Aux 4 Fromages Leader Snack",
                    "quantity": "300 g",
                },
                {
                    "_id": "1234567890",
                    "code": "1234567890",
                    "product_name": "Fusilli Aux 4 Fromages Leader Snack",
                    "quantity": "300 g",
                },
            ),
            # Test with projection
            (
                "1234567890",
                ["product_name"],
                {
                    "_id": "1234567890",
                    "product_name": "Fusilli Aux 4 Fromages Leader Snack",
                },
                {
                    "_id": "1234567890",
                    "product_name": "Fusilli Aux 4 Fromages Leader Snack",
                },
            ),
            # Test that we convert the `images` field to the legacy schema
            (
                "1234567890",
                None,
                {
                    "_id": "1234567890",
                    "code": "1234567890",
                    "product_name": "Fusilli Aux 4 Fromages Leader Snack",
                    "quantity": "300 g",
                    "images": IMAGES_WITH_NEW_SCHEMA,
                },
                {
                    "_id": "1234567890",
                    "code": "1234567890",
                    "product_name": "Fusilli Aux 4 Fromages Leader Snack",
                    "quantity": "300 g",
                    "images": IMAGES_WITH_LEGACY_SCHEMA,
                },
            ),
        ],
    )
    def test_get_product(self, barcode, projection, db_output, expected_output):
        server_type = ServerType.off
        client = {server_type: MagicMock()}
        client[server_type].products.find_one.return_value = db_output
        db = DBProductStore(server_type, client)

        product = db.get_product(
            ProductIdentifier(barcode=barcode, server_type=server_type),
            projection=projection,
        )
        assert product == expected_output

        if projection:
            assert client[server_type].products.find_one.call_count == 1
            assert client[server_type].products.find_one.call_args[0][1] == [
                "product_name"
            ]
