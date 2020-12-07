from robotoff.robotoff.products import ProductDataset
from robotoff.robotoff.insights.extraction import get_logger, requests
from robotoff.robotoff.insights.ocr.core import get_json_for_image

logger = get_logger(__name__)


def update_recycling(username, password):
    """
    Function to update "Recycle" image for the product
    based on triggers

    :param username:
    :param password:
    :return:
    """

    recycling_triggers = {
        "en": ["throw away", "recycle"],
        "fr": ["consignesdetri.fr", "recycler", "jeter", "bouteille"],
    }
    # get products dataset
    dataset = ProductDataset.load()

    # iterate products
    for product in dataset.stream().filter_nonempty_text_field("code"):

        if "packaging-photo-to-be-selected" in product.get("states", ""):
            images = get_images(product.get("code"))
            if images:
                images_ids = [
                    i
                    for i, j in images.get("product", {}).get("images", {}).items()
                    if not j.get("imgid")
                ]
                pack_images = {
                    i: j
                    for i, j in images.get("product", {}).get("images", {}).items()
                    if "packaging" in i
                }
                images_ids = list(set(images_ids))

                for i in images_ids:
                    # imageid - i, product
                    for lang in recycling_triggers.keys():

                        if check_image_in_pack(i, lang, pack_images):
                            continue

                        select_image(
                            product.get("code"),
                            i,
                            product,
                            lang,
                            recycling_triggers[lang],
                            pack_images,
                            username,
                            password,
                        )


def get_images(ean):
    """
    Get images for the product

    :param ean:
    :return:
    """
    url = (
        "https://world.openfoodfacts.org/api/v0/product/" + ean + ".json?fields=images"
    )
    try:
        r = requests.get(url)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}


def select_image(
    ean, image, product, lang, recycling_triggers, pack_images, username, password
):
    """
    Find "Recycle" image and select for the product

    :param ean:
    :param image: imgid
    :param product: object from dataset
    :param lang: en/fr/...
    :param recycling_triggers: ["throw away", "recycle"]
    :param pack_images_keys: dict_keys to check if unselect is needed
    :param username:
    :param password:
    :return:
    """
    field = "packaging_{}".format(lang)

    data = get_json_for_image(product.get("code"), image)
    image_text = data.get("responses", [])
    if image_text:
        image_text = image_text[0].get("fullTextAnnotation", {}).get("text", "")

        if any([1 if i in image_text.lower() else 0 for i in recycling_triggers]):
            ru = None
            if field in pack_images.keys():
                ru = unselect_image(ean, field, username, password)

            r = reselect_image(ean, field, image, username, password)

            if r:
                if ru:
                    logger.info(
                        "Recycle image(changed): ",
                        ean,
                        field,
                        pack_images[field].get("imgid"),
                        "->",
                        image,
                    )
                else:
                    logger.info("Recycle image(selected): ", ean, field, "->", image)


def check_image_in_pack(image, lang, pack_images):
    """
    Check if image has been already selected

    :param image: imgid
    :param lang: en/fr/...
    :param pack_images: image ids [packaging_en, front_en]
    :return:
    """
    if "packaging_{}".format(lang) in pack_images:
        current_id = pack_images.get("packaging_{}".format(lang), {}).get("imgid")
        if current_id == image:
            return True

    return False


def unselect_image(barcode, field_name, username, password):
    """
    Unselect image for product

    :param barcode: ean
    :param field_name: packaging_en
    :param username:
    :param password:
    :return:
    """

    url = "https://world.openfoodfacts.org/cgi/product_image_unselect.pl"
    data = {
        "code": barcode,
        "id": field_name,
        "user_id": username,
        "password": password,
    }
    try:
        r = requests.post(url, data=data)
        if r.ok:
            return True
    except Exception:
        logger.warn(
            "Exception in unselect_image: barcode - {}, id - {}".format(
                barcode, field_name
            )
        )

    return False


def reselect_image(barcode, field_name, img_id, username, password):
    """
    Select image for product

    :param barcode: ean
    :param field_name: packaging_en
    :param img_id: imgid=[0, 1, 2]
    :param username:
    :param password:
    :return:
    """

    if img_id:
        url = "https://world.openfoodfacts.org/cgi/product_image_crop.pl"
        data = {
            "code": barcode,
            "imgid": img_id,
            "id": field_name,
            "user_id": username,
            "password": password,
        }
        try:
            r = requests.post(url, data=data)
            if r.ok:
                return True
        except Exception:
            logger.warn(
                "Exception in reselect_image: barcode - {}, id - {}, imgid - {}".format(
                    barcode, field_name, img_id
                )
            )

    return False
