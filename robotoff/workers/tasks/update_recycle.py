from typing import Dict

import requests

from robotoff.insights.extraction import get_logger
from robotoff.prediction.ocr.core import get_json_for_image
from robotoff.products import ProductDataset
from robotoff.settings import BaseURLProvider

logger = get_logger(__name__)


def update_recycling(username: str, password: str) -> None:
    """
    Function to update "Recycle" image for the product based on triggers
    """

    recycling_triggers = {
        "en": ["throw away", "recycle"],
        "fr": ["consignesdetri.fr", "recycler", "jeter", "bouteille"],
    }
    # get products dataset
    dataset = ProductDataset.load()

    # iterate products
    for product in dataset.stream().filter_nonempty_text_field("code"):
        if "packaging-photo-to-be-selected" not in product.get("states", ""):
            continue

        product_code = product.get("code")
        if not product_code:
            continue

        images = get_images(product_code)
        if not images:
            continue

        product_images_items = images.get("product", {}).get("images", {}).items()
        images_ids = {i for i, j in product_images_items if not j.get("imgid")}
        pack_images = {i: j for i, j in product_images_items if "packaging" in i}

        for i in images_ids:
            # imageid - i, product
            for lang in recycling_triggers.keys():
                field = "packaging_{}".format(lang)

                if check_image_in_pack(i, field, pack_images):
                    continue

                if not check_trigger_in_text(product_code, i, recycling_triggers[lang]):
                    continue

                select_image(product_code, i, field, pack_images, username, password)


def get_images(ean: str) -> Dict:
    """
    Get images for the product
    """

    url = BaseURLProvider().get() + "/api/v0/product/" + ean + ".json?fields=images"
    try:
        result = requests.get(url)
        if result.ok:
            return result.json()
    except requests.RequestException:
        logger.warning("Exception in get_images: ean - %s", ean)
    return {}


def select_image(
    ean: str, img_id: str, field: str, pack_images: dict, username: str, password: str
) -> None:
    """
    Find "Recycle" image and select for the product
    """

    result_unselect_image = None

    if field in pack_images:
        result_unselect_image = unselect_image(ean, field, username, password)

    result_reselect_image = reselect_image(ean, field, img_id, username, password)

    if result_reselect_image and result_unselect_image:
        logger.info(
            "Recycle image(changed): %s %s %s %s %s",
            ean,
            field,
            pack_images[field].get("imgid"),
            "->",
            img_id,
        )
    elif result_reselect_image:
        logger.info("Recycle image(selected): %s %s %s %s", ean, field, "->", img_id)


def check_trigger_in_text(ean: str, img_id: str, recycling_triggers: list) -> bool:
    """
    Check "recycle" trigger from list of triggers in text annotation
    """

    data = get_json_for_image(ean, img_id)
    if data:
        image_text = data.get("responses", [])
        if image_text:
            image_text = image_text[0].get("fullTextAnnotation", {}).get("text", "")

            if any(trigger in image_text.lower() for trigger in recycling_triggers):
                return True

    return False


def check_image_in_pack(img_id: str, field: str, pack_images: dict) -> bool:
    """
    Check if image has been already selected
    """

    current_id = pack_images.get(field, {}).get("imgid")
    if current_id == img_id:
        return True

    return False


def unselect_image(barcode: str, field_name: str, username: str, password: str) -> bool:
    """
    Unselect image for product
    """

    url = BaseURLProvider().get() + "/cgi/product_image_unselect.pl"
    data = {
        "code": barcode,
        "id": field_name,
        "user_id": username,
        "password": password,
    }
    try:
        result = requests.post(url, data=data)
        return result.ok
    except requests.RequestException:
        logger.warning(
            "Exception in unselect_image: barcode - %s, id - %s", barcode, field_name
        )
    return False


def reselect_image(
    barcode: str, field_name: str, img_id: str, username: str, password: str
) -> bool:
    """
    Select image for product
    """

    url = BaseURLProvider().get() + "/cgi/product_image_crop.pl"
    data = {
        "code": barcode,
        "imgid": img_id,
        "id": field_name,
        "user_id": username,
        "password": password,
    }
    try:
        result = requests.post(url, data=data)
        return result.ok
    except requests.RequestException:
        logger.warning(
            "Exception in reselect_image: barcode - %s, id - %s, imgid - %s",
            barcode,
            field_name,
            img_id,
        )
    return False
