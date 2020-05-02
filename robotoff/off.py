import enum
import re
from typing import List, Dict, Optional, Tuple, Union

import requests

from robotoff import settings
from robotoff.utils import get_logger


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


class ServerType(enum.Enum):
    off = 1
    obf = 2
    opff = 3
    opf = 4


http_session = requests.Session()
USER_AGENT_HEADERS = {
    "User-Agent": settings.ROBOTOFF_USER_AGENT,
}
http_session.headers.update(USER_AGENT_HEADERS)

AUTH = ("roboto-app", settings.OFF_PASSWORD)
AUTH_DICT = {
    "user_id": AUTH[0],
    "password": AUTH[1],
}

API_URLS: Dict[ServerType, str] = {
    ServerType.off: "https://world.openfoodfacts.org",
    ServerType.obf: "https://world.openbeautyfacts.org",
    ServerType.opf: "https://world.openproductfacts.org",
    ServerType.opff: "https://world.openpetfoodfacts.org",
}

logger = get_logger(__name__)


BARCODE_PATH_REGEX = re.compile(r"^(...)(...)(...)(.*)$")


def get_product_update_url(server: Union[ServerType, str]) -> str:
    return "{}/cgi/product_jqm2.pl".format(get_base_url(server))


def get_product_image_select(server: Union[ServerType, str]) -> str:
    return "{}/cgi/product_image_crop.pl".format(get_base_url(server))


def get_api_product_url(server: Union[ServerType, str]) -> str:
    return "{}/api/v0/product".format(get_base_url(server))


def get_base_url(server: Union[ServerType, str]) -> str:
    if isinstance(server, str):
        server = server.replace("api", "world")
        return "https://{}".format(server)
    else:
        if server not in API_URLS:
            raise ValueError("unsupported server type: {}".format(server))

        return API_URLS[server]


def get_server_type(server_domain: str) -> ServerType:
    """Return the server type (off, obf, opff, opf) associated with the server
    domain, or None if the server_domain was not recognized."""
    server_split = server_domain.split(".")

    if len(server_split) == 3:
        subdomain, domain, tld = server_split

        if domain == "openfoodfacts":
            return ServerType.off
        elif domain == "openbeautyfacts":
            return ServerType.obf
        elif domain == "openpetfoodfacts":
            return ServerType.opff
        elif domain == "openproductsfacts":
            return ServerType.opf

    raise ValueError("unknown server domain: {}".format(server_domain))


def split_barcode(barcode: str) -> List[str]:
    if not barcode.isdigit():
        raise ValueError("unknown barcode format: {}".format(barcode))

    match = BARCODE_PATH_REGEX.fullmatch(barcode)

    if match:
        return [x for x in match.groups() if x]

    return [barcode]


def generate_json_ocr_url(barcode: str, image_name: str) -> str:
    splitted_barcode = split_barcode(barcode)
    path = "/{}/{}.json".format("/".join(splitted_barcode), image_name)
    return settings.OFF_IMAGE_BASE_URL + path


def generate_image_url(barcode: str, image_name: str) -> str:
    splitted_barcode = split_barcode(barcode)
    path = "/{}/{}.jpg".format("/".join(splitted_barcode), image_name)
    return settings.OFF_IMAGE_BASE_URL + path


def is_valid_image(barcode: str, image_id: str) -> bool:
    product = get_product(barcode, fields=["images"])

    if product is None:
        return False

    images = product.get("images", {})

    return image_id in images


def get_product(
    barcode: str,
    fields: List[str] = None,
    server: Optional[Union[ServerType, str]] = None,
) -> Optional[Dict]:
    fields = fields or []

    if server is None:
        server = ServerType.off

    url = get_api_product_url(server) + "/{}.json".format(barcode)

    if fields:
        # requests escape comma in URLs, as expected, but openfoodfacts server
        # does not recognize escaped commas.
        # See https://github.com/openfoodfacts/openfoodfacts-server/issues/1607
        url += "?fields={}".format(",".join(fields))

    r = http_session.get(url)

    if r.status_code != 200:
        return None

    data = r.json()

    if data["status_verbose"] != "product found":
        return None

    return data["product"]


def add_category(
    barcode: str, category: str, insight_id: Optional[str] = None, **kwargs
):
    comment = "[robotoff] Adding category '{}'".format(category)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "add_categories": category,
        "comment": comment,
    }
    update_product(params, **kwargs)


def update_quantity(
    barcode: str, quantity: str, insight_id: Optional[str] = None, **kwargs
):
    comment = "[robotoff] Updating quantity to '{}'".format(quantity)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "quantity": quantity,
        "comment": comment,
    }
    update_product(params, **kwargs)


def update_emb_codes(
    barcode: str, emb_codes: List[str], insight_id: Optional[str] = None, **kwargs
):
    emb_codes_str = ",".join(emb_codes)

    comment = "[robotoff] Adding packager codes '{}'".format(emb_codes_str)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "emb_codes": emb_codes_str,
        "comment": comment,
    }
    update_product(params, **kwargs)


def update_expiration_date(
    barcode: str, expiration_date: str, insight_id: Optional[str] = None, **kwargs
):
    comment = "[robotoff] Adding expiration date '{}'".format(expiration_date)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "expiration_date": expiration_date,
        "comment": comment,
    }
    update_product(params, **kwargs)


def add_label_tag(
    barcode: str, label_tag: str, insight_id: Optional[str] = None, **kwargs
):
    comment = "[robotoff] Adding label tag '{}'".format(label_tag)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "add_labels": label_tag,
        "comment": comment,
    }
    update_product(params, **kwargs)


def add_brand(barcode: str, brand: str, insight_id: Optional[str] = None, **kwargs):
    comment = "[robotoff] Adding brand '{}'".format(brand)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "add_brands": brand,
        "comment": comment,
    }
    update_product(params, **kwargs)


def add_store(barcode: str, store: str, insight_id: Optional[str] = None, **kwargs):
    comment = "[robotoff] Adding store '{}'".format(store)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "add_stores": store,
        "comment": comment,
    }
    update_product(params, **kwargs)


def add_packaging(
    barcode: str, packaging: str, insight_id: Optional[str] = None, **kwargs
):
    comment = "[robotoff] Adding packaging '{}'".format(packaging)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        "code": barcode,
        "add_packaging": packaging,
        "comment": comment,
    }
    update_product(params, **kwargs)


def save_ingredients(
    barcode: str,
    ingredient_text: str,
    insight_id: Optional[str] = None,
    lang: str = None,
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
        "code": barcode,
        "comment": comment,
        ingredient_key: ingredient_text,
    }
    update_product(params, **kwargs)


def update_product(
    params: Dict,
    server_domain: Optional[str] = None,
    auth: Optional[OFFAuthentication] = None,
):
    if server_domain is None:
        server_domain = settings.OFF_SERVER_DOMAIN

    url = get_product_update_url(server_domain)

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
        params.update(AUTH_DICT)

        if comment:
            params["comment"] = comment + " (automated edit)"

    if cookies is None and not params.get("password"):
        raise ValueError(
            "a password or a session cookie is required to update a product"
        )

    request_auth: Optional[Tuple[str, str]] = None
    if server_domain.endswith("openfoodfacts.net"):
        # dev environment requires authentication
        request_auth = ("off", "off")

    r = http_session.get(url, params=params, auth=request_auth, cookies=cookies)

    r.raise_for_status()
    json = r.json()

    status = json.get("status_verbose")

    if status != "fields saved":
        logger.warn("Unexpected status during product update: {}".format(status))


def move_to(barcode: str, to: ServerType) -> bool:
    if get_product(barcode, server=to) is not None:
        return False

    url = "{}/cgi/product_jqm.pl".format(settings.OFF_BASE_WEBSITE_URL)
    params = {
        "type": "edit",
        "code": barcode,
        "new_code": to,
        **AUTH_DICT,
    }
    r = http_session.get(url, params=params)
    data = r.json()
    return data["status"] == 1


def select_rotate_image(
    barcode: str,
    image_id: str,
    image_key: Optional[str] = None,
    rotate: Optional[int] = None,
    server_domain: Optional[str] = None,
    auth: Optional[OFFAuthentication] = None,
):
    if server_domain is None:
        server_domain = settings.OFF_SERVER_DOMAIN

    url = get_product_image_select(server_domain)
    cookies = None
    params = {
        "code": barcode,
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
        params.update(AUTH_DICT)

    if cookies is None and not params.get("password"):
        raise ValueError(
            "a password or a session cookie is required to select an image"
        )

    request_auth: Optional[Tuple[str, str]] = None
    if server_domain.endswith("openfoodfacts.net"):
        # dev environment requires authentication
        request_auth = ("off", "off")

    r = http_session.post(url, data=params, auth=request_auth, cookies=cookies)

    r.raise_for_status()
    return r
