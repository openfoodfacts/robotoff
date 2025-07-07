"""Interacting with OFF server to eg. update products or get infos"""

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from openfoodfacts.images import split_barcode
from requests.exceptions import JSONDecodeError

from robotoff import settings
from robotoff.types import (
    JSONType,
    NutrientData,
    ProductIdentifier,
    ProductTypeLiteral,
    ServerType,
)
from robotoff.utils import get_logger, http_session

logger = get_logger(__name__)


class OFFAuthentication:
    def __init__(
        self,
        session_cookie: str | None = None,
        username: str | None = None,
        password: str | None = None,
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

    def get_username(self) -> str | None:
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


def get_source_from_url(url: str) -> str:
    """Get the `source_image` field from an image or OCR URL.

    It's the path of the image or OCR JSON file, but without the `/images/products`
    prefix. It always ends with `.jpg`, whather it's an image or an OCR JSON file.

    :param url: the URL of the image or OCR JSON file
    :return: the source image path
    """
    url_path = urlparse(url).path

    if url_path.startswith("/images/products"):
        url_path = url_path[len("/images/products") :]

    if url_path.endswith(".json"):
        url_path = str(Path(url_path).with_suffix(".jpg"))

    return url_path


def _generate_file_path(product_id: ProductIdentifier, image_id: str, suffix: str):
    splitted_barcode = split_barcode(product_id.barcode)
    return f"/{'/'.join(splitted_barcode)}/{image_id}{suffix}"


def generate_image_path(product_id: ProductIdentifier, image_id: str) -> str:
    """Generate an image path.

    It's used to generate a unique identifier of an image for a product (and
    to generate an URL to fetch this image from the server).

    :param product_id: the product identifier
    :param image_id: the image ID (ex: `1`, `ingredients_fr.full`,...)
    :return: the full image path
    """
    return _generate_file_path(product_id, image_id, ".jpg")


def generate_json_ocr_path(product_id: ProductIdentifier, image_id: str) -> str:
    """Generate a JSON OCR path.

    It's used to generate a unique identifier of an OCR results for a product
    (and to generate an URL to fetch this OCR JSON from the server).

    :param product_id: the product identifier
    :param image_id: the image ID (ex: `1`, `ingredients_fr.full`,...)
    :return: the full image path
    """
    return _generate_file_path(product_id, image_id, ".json")


def generate_json_ocr_url(product_id: ProductIdentifier, image_id: str) -> str:
    """Generate the OCR JSON URL for a specific product and
    image ID.

    :param product_id: the product identifier
    :param image_id: the image ID (ex: `1`, `2`,...)
    :return: the generated image URL
    """
    return settings.BaseURLProvider.image_url(
        product_id.server_type, generate_json_ocr_path(product_id, image_id)
    )


def generate_image_url(product_id: ProductIdentifier, image_id: str) -> str:
    """Generate the image URL for a specific product and
    image ID.

    :param product_id: the product identifier
    :param image_id: the image ID (ex: `1`, `ingredients_fr.full`,...)
    :return: the generated image URL
    """
    return settings.BaseURLProvider.image_url(
        product_id.server_type, generate_image_path(product_id, image_id)
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
    fields: list[str] | None = None,
    timeout: int | None = 10,
) -> dict | None:
    fields = fields or []

    # V2 of API is required to have proper ingredient nesting
    # for product categorization
    base_url = settings.BaseURLProvider.world(product_id.server_type)
    url = f"{base_url}/api/v2/product/{product_id.barcode}"

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


def generate_edit_comment(
    action: str,
    is_vote: bool,
    is_automatic: bool,
    insight_id: str | None = None,
) -> str:
    """Generate the edit comment to be sent to Product Opener.

    :param action: A description of the edit
    :param is_vote: whether the edit was triggered from an insight vote
    :param is_automatic: whether the edit was performed automatically (without
        human) supervision
    :param insight_id: the ID of the insight, if any, defaults to None
    :return: the edit comment
    """
    comment = f"[robotoff] {action}"

    if insight_id:
        comment += f", ID: {insight_id}"

    if is_vote:
        comment += " (applied after 3 anonymous votes)"
    elif is_automatic:
        comment += " (automated edit)"

    return comment


def add_category(
    product_id: ProductIdentifier,
    category: str,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    comment = generate_edit_comment(
        f"Adding category '{category}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "add_categories": category,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def update_quantity(
    product_id: ProductIdentifier,
    quantity: str,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    comment = generate_edit_comment(
        f"Updating quantity to '{quantity}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "quantity": quantity,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def update_emb_codes(
    product_id: ProductIdentifier,
    emb_codes: list[str],
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    emb_codes_str = ",".join(emb_codes)
    comment = generate_edit_comment(
        f"Adding packager codes '{emb_codes_str}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "emb_codes": emb_codes_str,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def update_expiration_date(
    product_id: ProductIdentifier,
    expiration_date: str,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    comment = generate_edit_comment(
        f"Adding expiration date '{expiration_date}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "expiration_date": expiration_date,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def add_label_tag(
    product_id: ProductIdentifier,
    label_tag: str,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    comment = generate_edit_comment(
        f"Adding label tag '{label_tag}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "add_labels": label_tag,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def add_brand(
    product_id: ProductIdentifier,
    brand: str,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    comment = generate_edit_comment(
        f"Adding brand '{brand}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "add_brands": brand,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def add_store(
    product_id: ProductIdentifier,
    store: str,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    comment = generate_edit_comment(
        f"Adding store '{store}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "add_stores": store,
        "comment": comment,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def add_packaging(
    product_id: ProductIdentifier,
    packaging: dict,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    shape_value_tag = packaging["shape"]["value_tag"]
    comment = generate_edit_comment(
        f"Updating/adding packaging elements '{shape_value_tag}'",
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
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
        product_id.barcode,
        body,
        server_type=product_id.server_type,
        auth=auth,
        **kwargs,
    )


def save_ingredients(
    product_id: ProductIdentifier,
    ingredient_text: str,
    insight_id: str | None = None,
    lang: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    base_comment: str | None = None,
    **kwargs,
) -> None:
    """Save the ingredients text for a product, by sending a request to
    Product Opener.

    :param product_id: the product identifier
    :param ingredient_text: the ingredients text to save
    :param insight_id: the ID of the insight associated with the change, if any,
        defaults to None. This is used to generate the edit comment.
    :param lang: the language of the ingredients text, defaults to None. This is
        used to determine the language-specific ingredient field to update.
    :param auth: the authentication data to use for the request, defaults to None.
    :param is_vote: whether the edit was triggered from an insight vote, defaults
        to False. This is used to generate the edit comment.
    :param base_comment: a base comment to use for the edit, defaults to None.
        By default, it will be set to "Update ingredients".
    :param kwargs: additional keyword arguments to pass to the update_product
        function.
    """
    ingredient_key = "ingredients_text" if lang is None else f"ingredients_text_{lang}"

    base_comment = base_comment or "Update ingredients"
    comment = generate_edit_comment(
        base_comment,
        is_vote=is_vote,
        is_automatic=auth is None,
        insight_id=insight_id,
    )
    params = {
        "code": product_id.barcode,
        "comment": comment,
        ingredient_key: ingredient_text,
    }
    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def save_nutrients(
    product_id: ProductIdentifier,
    nutrient_data: NutrientData,
    insight_id: str | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    **kwargs,
):
    """Save nutrient information for a product."""
    comment = generate_edit_comment(
        "Update nutrient values", is_vote, auth is None, insight_id
    )
    params = {
        "code": product_id.barcode,
        "comment": comment,
        "nutrition_data_per": nutrient_data.nutrition_data_per,
    }
    if nutrient_data.serving_size:
        params["serving_size"] = nutrient_data.serving_size

    for nutrient_name, nutrient_value in nutrient_data.nutrients.items():
        if nutrient_value.unit:
            params[f"nutriment_{nutrient_name}"] = nutrient_value.value
            params[f"nutriment_{nutrient_name}_unit"] = nutrient_value.unit

    update_product(params, server_type=product_id.server_type, auth=auth, **kwargs)


def update_product(
    params: dict,
    server_type: ServerType,
    auth: OFFAuthentication | None = None,
    timeout: int | None = 15,
):
    base_url = settings.BaseURLProvider.world(server_type)
    url = f"{base_url}/cgi/product_jqm2.pl"

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

    if cookies is None and not params.get("password"):
        raise ValueError(
            "a password or a session cookie is required to update a product"
        )
    r = http_session.post(
        url,
        data=params,
        auth=settings._off_request_auth,
        cookies=cookies,
        timeout=timeout,
    )

    r.raise_for_status()
    try:
        json = r.json()
    except JSONDecodeError as e:
        logger.info(
            "Error during OFF update request JSON decoding, text response: '%s'", r.text
        )
        raise e

    status = json.get("status_verbose")

    if status != "fields saved":
        logger.warning(
            "Unexpected status during product update: %s",
            status,
            extra={"response_json": json, "request_headers": r.request.headers},
        )


def update_product_v3(
    barcode: str,
    body: dict,
    server_type: ServerType,
    auth: OFFAuthentication | None = None,
    timeout: int | None = 15,
):
    base_url = settings.BaseURLProvider.world(server_type)
    url = f"{base_url}/api/v3/product/{barcode}"

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
    try:
        json = r.json()
    except JSONDecodeError as e:
        logger.info(
            "Error during OFF update request JSON decoding, text response: '%s'", r.text
        )
        raise e

    if json.get("errors"):
        raise ValueError("Errors during product update: %s", str(json["errors"]))


def move_to(
    product_id: ProductIdentifier, to: ServerType, timeout: int | None = 10
) -> bool:
    if (
        get_product(ProductIdentifier(barcode=product_id.barcode, server_type=to))
        is not None
    ):
        return False

    base_url = settings.BaseURLProvider.world(product_id.server_type)
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
    auth: OFFAuthentication | None,
    timeout: int | None = 15,
) -> requests.Response:
    """Unselect an image.

    :param product_id: identifier of the product
    :param image_field: field name of the image to unselect, ex: front_fr
    :param auth: user authentication data
    :param timeout: request timeout value in seconds, defaults to 15s
    :return: the request Response
    """
    base_url = settings.BaseURLProvider.world(product_id.server_type)
    url = f"{base_url}/cgi/product_image_unselect.pl"
    cookies = None
    params = {
        "code": product_id.barcode,
        "id": image_field,
    }

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
    timeout: int | None = 15,
) -> requests.Response:
    """Delete an image on Product Opener.

    :param product_id: identifier of the product
    :param image_id: ID of the image to delete (number)
    :param auth: user authentication data
    :param timeout: request timeout (in seconds), defaults to 15
    :return: the requests Response
    """

    base_url = settings.BaseURLProvider.world(product_id.server_type)
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
    image_key: str | None = None,
    rotate: int | None = None,
    crop_bounding_box: tuple[float, float, float, float] | None = None,
    auth: OFFAuthentication | None = None,
    is_vote: bool = False,
    insight_id: str | None = None,
    timeout: int | None = 30,
):
    base_url = settings.BaseURLProvider.world(product_id.server_type)
    url = f"{base_url}/cgi/product_image_crop.pl"
    cookies = None
    params: JSONType = {
        "code": product_id.barcode,
        "imgid": image_id,
        "comment": generate_edit_comment(
            f"Selecting image {image_id} as {image_key}",
            is_vote=is_vote,
            is_automatic=auth is None,
            insight_id=insight_id,
        ),
        # We need to tell Product Opener that the bounding box coordinates are
        # related to the full image
        "coordinates_image_size": "full",
    }

    if rotate is not None and rotate != 0:
        if rotate not in (90, 180, 270):
            raise ValueError(f"invalid value for rotation angle: {rotate}")
        params["angle"] = str(rotate)

    if crop_bounding_box is not None:
        y_min, x_min, y_max, x_max = crop_bounding_box
        params["x1"] = x_min
        params["y1"] = y_min
        params["x2"] = x_max
        params["y2"] = y_max

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
    auth: OFFAuthentication | None = None,
):
    base_url = settings.BaseURLProvider.world(product_id.server_type)
    url = f"{base_url}/cgi/product_image_upload.pl"

    form_data: dict[str, tuple[str | None, Any]] = {}

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


def parse_ingredients(text: str, lang: str, timeout: int = 10) -> list[JSONType]:
    """Parse ingredients text using Product Opener API.

    It is only available for `off` flavor (food).

    The result is a list of ingredients, each ingredient is a dict with the
    following keys:

    - id: the ingredient ID. Having an ID does not means that the ingredient
        is recognized, you must check if it exists in the taxonomy.
    - text: the ingredient text (as it appears in the input ingredients list)
    - percent_min: the minimum percentage of the ingredient in the product
    - percent_max: the maximum percentage of the ingredient in the product
    - percent_estimate: the estimated percentage of the ingredient in the
        product
    - vegan (bool): optional key indicating if the ingredient is vegan
    - vegetarian (bool): optional key indicating if the ingredient is
        vegetarian


    :param server_type: the server type (project) to use
    :param text: the ingredients text to parse
    :param lang: the language of the text (used for parsing) as a 2-letter code
    :param timeout: the request timeout in seconds, defaults to 10s
    :raises RuntimeError: a RuntimeError is raised if the parsing fails
    :return: the list of parsed ingredients
    """
    base_url = settings.BaseURLProvider.world(ServerType.off)
    # by using "test" as code, we don't save any information to database
    # This endpoint is specifically designed for testing purposes
    url = f"{base_url}/api/v3/product/test"

    if len(text) == 0:
        raise ValueError("text must be a non-empty string")

    try:
        r = http_session.patch(
            url,
            auth=settings._off_request_auth,
            json={
                "fields": "ingredients",
                "lc": lang,
                "tags_lc": lang,
                "product": {
                    "lang": lang,
                    f"ingredients_text_{lang}": text,
                },
            },
            timeout=timeout,
        )
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.SSLError,
        requests.exceptions.Timeout,
    ) as e:
        raise RuntimeError(
            f"Unable to parse ingredients: error during HTTP request: {e}"
        )

    if not r.ok:
        raise RuntimeError(
            f"Unable to parse ingredients (non-200 status code): {r.status_code}, {r.text}"
        )

    response_data = r.json()

    if response_data.get("status") != "success":
        raise RuntimeError(f"Unable to parse ingredients: {response_data}")

    return response_data["product"].get("ingredients", [])


def get_product_type(
    product_id: ProductIdentifier, timeout: int = 5
) -> ProductTypeLiteral | None:
    """Retrieve the product type for a given product identifier.

    The function will return the product type if found or None if the product does not
    exist.

    We send a request to the Product Opener API on the server associated with the
    product identifier's server type (ex: world.openfoodfacts.org for food,
    world.openbeautyfacts.org for beauty, etc.).

    If the product type matches the server type associated with the product identifier,
    Product Opener returns the product as expected.
    Otherwise, it returns an HTTP 404 error, with the product type in the
    `errors` list of the response. This feature is only available on the v3 of the API.

    If the product was not found (irrespective of the product type), the API returns a
    404 status code with no `errors` field. This allows us to know if the product still
    exists and what is the real product type of the product using the v3 API.

    :param product_id: the product identifier
    :param timeout: the request timeout in seconds, defaults to 5s
    :raises RuntimeError: if the request fails or returns an unexpected status code
    :return: the product type if found, otherwise None
    """
    base_url = settings.BaseURLProvider.world(product_id.server_type)
    url = f"{base_url}/api/v3.4/product/{product_id.barcode}?fields=product_type"
    try:
        r = http_session.get(
            url,
            auth=settings._off_request_auth,
            timeout=timeout,
        )
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.SSLError,
        requests.exceptions.Timeout,
    ) as e:
        raise RuntimeError(
            f"Unable to get product type: error during HTTP request: {e}"
        )

    if r.status_code not in (200, 404):
        raise RuntimeError(
            f"Unable to get product type (non-200/404 status code): {r.status_code}, {r.text}"
        )
    response_data = r.json()

    if response_data.get("status") == "success":
        return response_data["product"]["product_type"]

    errors = [
        e for e in response_data.get("errors", []) if e["field"]["id"] == "product_type"
    ]
    if errors:
        error = errors[0]
        return error["field"]["value"]

    return None


def normalize_tag(value, lowercase=True):
    """Given a value normalize it to a tag (as in taxonomies).

    This means removing accents, lowercasing, replacing spaces with dashes,
    etc..
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
