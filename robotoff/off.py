"""Interacting with OFF server to eg. update products or get infos
"""
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from robotoff import settings
from robotoff.types import ProductIdentifier, ServerType
from robotoff.utils import get_logger, http_session

logger = get_logger(__name__)


class OFFAuthentication:
    def __init__(
        self,
        session_cookie: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if session_cookie is None and username is None and password is None:
            raise ValueError(
                "one of session_cookie or credentials (username and password) must be provided"
            )

        self.session_cookie = session_cookie
        self.username = username
        self.password = password

    def __eq__(self, other):
        """equality - we may use it in tests"""
        return (
            self.username == other.username
            and self.password == other.password
            and self.session_cookie == other.session_cookie
        )

    def get_username(self) -> Optional[str]:
        if self.username is not None:
            return self.username

        elif self.session_cookie is not None:
            splitted = self.session_cookie.split("&")

            if splitted:
                is_next = False
                for split in splitted:
                    if split == "user_id":
                        is_next = True
                        continue
                    elif is_next:
                        if split:
                            return split
                        else:
                            break

            logger.warning(
                "Unable to extract username from session cookie: %s",
                self.session_cookie,
            )

        return None


BARCODE_PATH_REGEX = re.compile(r"^(...)(...)(...)(.*)$")


def get_source_from_url(ocr_url: str) -> str:
    url_path = urlparse(ocr_url).path

    if url_path.startswith("/images/products"):
        url_path = url_path[len("/images/products") :]

    if url_path.endswith(".json"):
        url_path = str(Path(url_path).with_suffix(".jpg"))

    return url_path


def get_barcode_from_url(url: str) -> Optional[str]:
    url_path = urlparse(url).path
    return get_barcode_from_path(url_path)


def get_barcode_from_path(path: str) -> Optional[str]:
    barcode = ""

    for parent in Path(path).parents:
        if parent.name.isdigit():
            barcode = parent.name + barcode
        else:
            break

    return barcode or None


def get_product_image_select_url(server_type: ServerType) -> str:
    base_url = settings.BaseURLProvider.api(server_type)
    return f"{base_url}/cgi/product_image_crop.pl"


def get_api_product_url(server_type: ServerType) -> str:
    # V2 of API is required to have proper ingredient nesting
    # for product categorization
    base_url = settings.BaseURLProvider.api(server_type)
    return f"{base_url}/api/v2/product"


def split_barcode(barcode: str) -> list[str]:
    if not barcode.isdigit():
        raise ValueError("unknown barcode format: {}".format(barcode))

    match = BARCODE_PATH_REGEX.fullmatch(barcode)

    if match:
        return [x for x in match.groups() if x]

    return [barcode]


def generate_image_path(barcode: str, image_id: str) -> str:
    splitted_barcode = split_barcode(barcode)
    return "/{}/{}.jpg".format("/".join(splitted_barcode), image_id)


def generate_json_path(barcode: str, image_id: str) -> str:
    splitted_barcode = split_barcode(barcode)
    return "/{}/{}.json".format("/".join(splitted_barcode), image_id)


def generate_json_ocr_url(product_id: ProductIdentifier, image_id: str) -> str:
    return (
        settings.BaseURLProvider.static(product_id.server_type)
        + f"/images/products{generate_json_path(product_id.barcode, image_id)}"
    )


def generate_image_url(product_id: ProductIdentifier, image_id: str) -> str:
    return settings.BaseURLProvider.image_url(
        product_id.server_type, generate_image_path(product_id.barcode, image_id)
    )


def is_valid_image(product_id: ProductIdentifier, image_id: str) -> bool:
    product = get_product(product_id, fields=["images"])

    if product is None:
        return False

    images = product.get("images", {})

    return image_id in images


def off_credentials() -> dict[str, str]:
    return {"user_id": settings._off_user, "password": settings._off_password}


def get_product(
    product_id: ProductIdentifier,
    fields: Optional[list[str]] = None,
    timeout: Optional[int] = 10,
) -> Optional[dict]:
    fields = fields or []

    url = get_api_product_url(product_id.server_type) + "/{}.json".format(
        product_id.barcode
    )

    if fields:
        # requests escape comma in URLs, as expected, but openfoodfacts server
        # does not recognize escaped commas.
        # See https://github.com/openfoodfacts/openfoodfacts-server/issues/1607
        url += "?fields={}".format(",".join(fields))

    r = http_session.get(url, timeout=timeout, auth=settings._off_request_auth)

    if r.status_code != 200:
        return None

    data = r.json()

    if data["status_verbose"] != "product found":
        return None

    return data["product"]


def add_category(
    product_id: ProductIdentifier,
    category: str,
    insight_id: Optional[str] = None,
    **kwargs,
):
    comment = "[robotoff] Adding category '{}'".format(category)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "add_categories": category,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def update_quantity(
    product_id: ProductIdentifier,
    quantity: str,
    insight_id: Optional[str] = None,
    **kwargs,
):
    comment = "[robotoff] Updating quantity to '{}'".format(quantity)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "quantity": quantity,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def update_emb_codes(
    product_id: ProductIdentifier,
    emb_codes: list[str],
    insight_id: Optional[str] = None,
    **kwargs,
):
    emb_codes_str = ",".join(emb_codes)

    comment = "[robotoff] Adding packager codes '{}'".format(emb_codes_str)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "emb_codes": emb_codes_str,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def update_expiration_date(
    product_id: ProductIdentifier,
    expiration_date: str,
    insight_id: Optional[str] = None,
    **kwargs,
):
    comment = "[robotoff] Adding expiration date '{}'".format(expiration_date)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "expiration_date": expiration_date,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def add_label_tag(
    product_id: ProductIdentifier,
    label_tag: str,
    insight_id: Optional[str] = None,
    **kwargs,
):
    comment = "[robotoff] Adding label tag '{}'".format(label_tag)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "add_labels": label_tag,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def add_brand(
    product_id: ProductIdentifier,
    brand: str,
    insight_id: Optional[str] = None,
    **kwargs,
):
    comment = "[robotoff] Adding brand '{}'".format(brand)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "add_brands": brand,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def add_store(
    product_id: ProductIdentifier,
    store: str,
    insight_id: Optional[str] = None,
    **kwargs,
):
    comment = "[robotoff] Adding store '{}'".format(store)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "add_stores": store,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def add_packaging(
    product_id: ProductIdentifier,
    packaging: dict,
    insight_id: Optional[str] = None,
    **kwargs,
):
    shape_value_tag = packaging["shape"]["value_tag"]
    comment = f"[robotoff] Updating/adding packaging elements '{shape_value_tag}'"

    if insight_id:
        comment += f", ID: {insight_id}"

    body = {
        "product": {
            "packagings_add": [
                {
                    prop: {"id": element.get("value_tag")}
                    for prop, element in packaging.items()
                    if element.get("value_tag")
                }
            ],
        },
        "fields": "none",
        "comment": comment,
    }
    update_product_v3(
        product_id.barcode, body, server_type=product_id.server_type, **kwargs
    )


def save_ingredients(
    product_id: ProductIdentifier,
    ingredient_text: str,
    insight_id: Optional[str] = None,
    lang: Optional[str] = None,
    comment: Optional[str] = None,
    **kwargs,
):
    ingredient_key = "ingredients_text" if lang is None else f"ingredients_text_{lang}"

    if comment:
        comment = "[robotoff] Ingredient spellcheck correction ({})".format(comment)
    else:
        comment = "[robotoff] Ingredient spellcheck correction"

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": product_id.barcode,
        "comment": comment,
        ingredient_key: ingredient_text,
    }
    update_product(params, server_type=product_id.server_type, **kwargs)


def update_product(
    params: dict,
    server_type: ServerType,
    auth: Optional[OFFAuthentication] = None,
    timeout: Optional[int] = 15,
):
    base_url = settings.BaseURLProvider.api(server_type)
    url = f"{base_url}/cgi/product_jqm2.pl"

    comment = params.get("comment")
    cookies = None

    if auth is not None:
        if auth.session_cookie:
            cookies = {
                "session": auth.session_cookie,
            }
        elif auth.username:
            params["user_id"] = auth.username
            params["password"] = auth.password
    else:
        params.update(off_credentials())

        if comment:
            params["comment"] = comment + " (automated edit)"

    if cookies is None and not params.get("password"):
        raise ValueError(
            "a password or a session cookie is required to update a product"
        )
    r = http_session.get(
        url,
        params=params,
        auth=settings._off_request_auth,
        cookies=cookies,
        timeout=timeout,
    )

    r.raise_for_status()
    json = r.json()

    status = json.get("status_verbose")

    if status != "fields saved":
        logger.warning("Unexpected status during product update: %s", status)


def update_product_v3(
    barcode: str,
    body: dict,
    server_type: ServerType,
    auth: Optional[OFFAuthentication] = None,
    timeout: Optional[int] = 15,
):
    base_url = settings.BaseURLProvider.api(server_type)
    url = f"{base_url}/api/v3/product/{barcode}"

    comment = body.get("comment")
    cookies = None

    if auth is not None:
        if auth.session_cookie:
            cookies = {
                "session": auth.session_cookie,
            }
        elif auth.username:
            body["user_id"] = auth.username
            body["password"] = auth.password
    else:
        body.update(off_credentials())

        if comment:
            body["comment"] = comment + " (automated edit)"

    if cookies is None and not body.get("password"):
        raise ValueError(
            "a password or a session cookie is required to update a product"
        )
    r = http_session.patch(
        url,
        json=body,
        auth=settings._off_request_auth,
        cookies=cookies,
        timeout=timeout,
    )

    r.raise_for_status()
    json = r.json()

    if json.get("errors"):
        raise ValueError("Errors during product update: %s", str(json["errors"]))


def move_to(
    product_id: ProductIdentifier, to: ServerType, timeout: Optional[int] = 10
) -> bool:
    if (
        get_product(ProductIdentifier(barcode=product_id.barcode, server_type=to))
        is not None
    ):
        return False

    base_url = settings.BaseURLProvider.api(product_id.server_type)
    url = f"{base_url}/cgi/product_jqm.pl"
    params = {
        "type": "edit",
        "code": product_id.barcode,
        "new_code": str(to),
        **off_credentials(),
    }
    r = http_session.get(url, params=params, timeout=timeout)
    data = r.json()
    return data["status"] == 1


def delete_image_pipeline(
    product_id: ProductIdentifier,
    image_id: str,
    auth: OFFAuthentication,
) -> None:
    """Delete an image and unselect all selected images that have this image
    as image ID.

    :param product_id: identifier of the product
    :param image_id: ID of the image to delete (number)
    :param auth: user authentication data
    """
    product = get_product(product_id, ["images"])

    if product is None:
        logger.info("%s not found, cannot delete image %s", product_id, image_id)
        return None

    to_delete = False
    to_unselect = []

    images = product["images"]
    if image_id in images:
        to_delete = True

    for image_field, image_data in (
        (key, data) for key, data in images.items() if not key.isdigit()
    ):
        if image_data["imgid"] == image_id:
            to_unselect.append(image_field)

    if to_delete:
        logger.info("Sending deletion request for image %s of %s", image_id, product_id)
        delete_image(product_id, image_id, auth)

    for image_field in to_unselect:
        logger.info(
            "Sending unselect request for image %s of %s", image_field, product_id
        )
        unselect_image(product_id, image_field, auth)

    logger.info("Image deletion pipeline completed")


def unselect_image(
    product_id: ProductIdentifier,
    image_field: str,
    auth: OFFAuthentication,
    timeout: Optional[int] = 15,
) -> requests.Response:
    """Unselect an image.

    :param product_id: identifier of the product
    :param image_field: field name of the image to unselect, ex: front_fr
    :param auth: user authentication data
    :param timeout: request timeout value in seconds, defaults to 15s
    :return: the request Response
    """
    base_url = settings.BaseURLProvider.api(product_id.server_type)
    url = f"{base_url}/cgi/product_image_unselect.pl"
    cookies = None
    params = {
        "code": product_id.barcode,
        "id": image_field,
    }

    if auth.session_cookie:
        cookies = {
            "session": auth.session_cookie,
        }
    elif auth.username and auth.password:
        params["user_id"] = auth.username
        params["password"] = auth.password

    r = http_session.post(
        url,
        data=params,
        auth=settings._off_request_auth,
        cookies=cookies,
        timeout=timeout,
    )

    r.raise_for_status()
    return r


def delete_image(
    product_id: ProductIdentifier,
    image_id: str,
    auth: OFFAuthentication,
    timeout: Optional[int] = 15,
) -> requests.Response:
    """Delete an image on Product Opener.

    :param product_id: identifier of the product
    :param image_id: ID of the image to delete (number)
    :param auth: user authentication data
    :param timeout: request timeout (in seconds), defaults to 15
    :return: the requests Response
    """

    base_url = settings.BaseURLProvider.api(product_id.server_type)
    url = f"{base_url}/cgi/product_image_move.pl"
    cookies = None
    params = {
        "type": "edit",
        "code": product_id.barcode,
        "imgids": image_id,
        "action": "process",
        "move_to_override": "trash",
    }
    form_data = {key: (None, value) for key, value in params.items()}

    if auth.session_cookie:
        cookies = {
            "session": auth.session_cookie,
        }
    elif auth.username and auth.password:
        params["user_id"] = auth.username
        params["password"] = auth.password

    r = http_session.post(
        url,
        auth=settings._off_request_auth,
        files=form_data,
        cookies=cookies,
        timeout=timeout,
    )

    r.raise_for_status()
    json_response = r.json()
    if json_response["status"] != "ok":
        logger.warning("error during image deletion: %s", json_response.get("error"))

    return r


def select_rotate_image(
    product_id: ProductIdentifier,
    image_id: str,
    image_key: Optional[str] = None,
    rotate: Optional[int] = None,
    auth: Optional[OFFAuthentication] = None,
    timeout: Optional[int] = 15,
):
    url = get_product_image_select_url(product_id.server_type)
    cookies = None
    params = {
        "code": product_id.barcode,
        "imgid": image_id,
    }

    if rotate is not None:
        if rotate not in (90, 180, 270):
            raise ValueError("invalid value for rotation angle: {}".format(rotate))

        params["angle"] = str(rotate)

    if image_key is not None:
        params["id"] = image_key

    if auth is not None:
        if auth.session_cookie:
            cookies = {
                "session": auth.session_cookie,
            }
        elif auth.username and auth.password:
            params["user_id"] = auth.username
            params["password"] = auth.password
    else:
        params.update(off_credentials())

    if cookies is None and not params.get("password"):
        raise ValueError(
            "a password or a session cookie is required to select an image"
        )

    r = http_session.post(
        url,
        data=params,
        auth=settings._off_request_auth,
        cookies=cookies,
        timeout=timeout,
    )

    r.raise_for_status()
    return r


def send_image(
    product_id: ProductIdentifier,
    image_field: str,
    image_fp,
    auth: Optional[OFFAuthentication] = None,
):
    base_url = settings.BaseURLProvider.world(product_id.server_type)
    url = f"{base_url}/cgi/product_image_upload.pl"

    form_data: dict[str, tuple[Optional[str], Any]] = {}

    if auth is not None and auth.username and auth.password:
        user_id = auth.username
        password = auth.password
    else:
        credentials = off_credentials()
        user_id = credentials["user_id"]
        password = credentials["password"]

    form_data["user_id"] = (None, user_id)
    form_data["password"] = (None, password)
    form_data["code"] = (None, product_id.barcode)
    form_data["imagefield"] = (None, image_field)
    form_data[f"imgupload_{image_field}"] = ("image.jpg", image_fp)

    r = http_session.post(
        url,
        auth=settings._off_request_auth,
        files=form_data,
    )
    return r


def normalize_tag(value, lowercase=True):
    """given a value normalize it to a tag (as in taxonomies)

    This means removing accents, lowercasing, replacing spaces with dashes, etc..
    """
    # removing accents
    value = re.sub(r"[¢£¤¥§©ª®°²³µ¶¹º¼½¾×‰€™]", "-", value)
    value = re.sub(r"[éè]", "e", value)
    value = re.sub(r"[à]", "a", value)
    value = re.sub(r"[ù]", "u", value)
    # changing unwanted character to "-"
    value = re.sub(r"&\w+;", "-", value)
    value = re.sub(
        r"[\s!\"#\$%&'()*+,\/:;<=>?@\[\\\]^_`{\|}~¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿×ˆ˜–—‘’‚“”„†‡•…‰‹›€™\t]",  # noqa: E501
        "-",
        value,
    )
    # lowering the value if wanted
    if lowercase:
        value = value.lower()
    # removing excess "-"
    value = re.sub(r"-+", "-", value)
    value = value.strip("-")
    return value
