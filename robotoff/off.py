import enum
import re
from typing import List, Dict, Optional

import requests

from robotoff import settings
from robotoff.utils import get_logger

http_session = requests.Session()
USER_AGENT_HEADERS = {
    'User-Agent': settings.ROBOTOFF_USER_AGENT,
}
http_session.headers.update(USER_AGENT_HEADERS)

AUTH = ("roboto-app", settings.OFF_PASSWORD)
AUTH_DICT = {
    'user_id': AUTH[0],
    'password': AUTH[1],
}

API_URL = "https://world.openfoodfacts.org/api/v0"
PRODUCT_URL = API_URL + "/product"

logger = get_logger(__name__)


BARCODE_PATH_REGEX = re.compile(r"^(...)(...)(...)(.*)$")


class ServerType(enum.Enum):
    off = 1
    obf = 2
    opff = 3
    opf = 4


def get_product_update_url(server_domain: str) -> str:
    server_domain = server_domain.replace('api', 'world')
    return "https://{}/cgi/product_jqm2.pl".format(server_domain)


def get_server_type(server_domain: str) -> Optional[ServerType]:
    """Return the server type (off, obf, opff, opf) associated with the server
    domain, or None if the server_domain was not recognized."""
    server_split = server_domain.split('.')

    if len(server_split) == 3:
        subdomain, domain, tld = server_split

        if domain == 'openfoodfacts':
            return ServerType.off
        elif domain == 'openbeautyfacts':
            return ServerType.obf
        elif domain == 'openpetfoodfacts':
            return ServerType.opff
        elif domain == 'openproductsfacts':
            return ServerType.opf

    logger.warning("unknown server domain: {}".format(server_domain))
    return None


def split_barcode(barcode: str) -> List[str]:
    if not barcode.isdigit():
        raise ValueError("unknown barcode format: {}".format(barcode))

    match = BARCODE_PATH_REGEX.fullmatch(barcode)

    if match:
        return [x for x in match.groups() if x]

    return [barcode]


def generate_json_ocr_url(barcode: str, image_name: str) -> str:
    splitted_barcode = split_barcode(barcode)
    path = "/{}/{}.json".format('/'.join(splitted_barcode), image_name)
    return settings.OFF_IMAGE_BASE_URL + path


def generate_image_url(barcode: str, image_name: str) -> str:
    splitted_barcode = split_barcode(barcode)
    path = "/{}/{}.jpg".format('/'.join(splitted_barcode), image_name)
    return settings.OFF_IMAGE_BASE_URL + path


def is_valid_image(barcode: str, image_id: str) -> bool:
    product = get_product(barcode, fields=['images'])

    if product is None:
        return False

    images = product.get('images', {})

    return image_id in images


def get_product(barcode: str, fields: List[str] = None) -> Optional[Dict]:
    # TODO: resolve url given server_domain parameter
    fields = fields or []
    url = PRODUCT_URL + "/{}.json".format(barcode)

    if fields:
        # requests escape comma in URLs, as expected, but openfoodfacts server
        # does not recognize escaped commas.
        # See https://github.com/openfoodfacts/openfoodfacts-server/issues/1607
        url += '?fields={}'.format(','.join(fields))

    r = http_session.get(url)

    if r.status_code != 200:
        return None

    data = r.json()

    if data['status_verbose'] != 'product found':
        return None

    return data['product']


def add_category(barcode: str, category: str,
                 insight_id: Optional[str] = None,
                 **kwargs):
    comment = "[robotoff] Adding category '{}'".format(category)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        'code': barcode,
        'add_categories': category,
        'comment': comment,
    }
    update_product(params, **kwargs)


def update_quantity(barcode: str, quantity: str,
                    insight_id: Optional[str] = None,
                    **kwargs):
    comment = "[robotoff] Updating quantity to '{}'".format(quantity)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        'code': barcode,
        'quantity': quantity,
        'comment': comment,
    }
    update_product(params, **kwargs)


def update_emb_codes(barcode: str, emb_codes: List[str],
                     insight_id: Optional[str] = None,
                     **kwargs):
    emb_codes_str = ','.join(emb_codes)

    comment = "[robotoff] Adding packager codes '{}'".format(emb_codes_str)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        'code': barcode,
        'emb_codes': emb_codes_str,
        'comment': comment,
    }
    update_product(params, **kwargs)


def update_expiration_date(barcode: str, expiration_date: str,
                           insight_id: Optional[str] = None,
                           **kwargs):
    comment = "[robotoff] Adding expiration date '{}'".format(expiration_date)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        'code': barcode,
        'expiration_date': expiration_date,
        'comment': comment,
    }
    update_product(params, **kwargs)


def add_label_tag(barcode: str, label_tag: str,
                  insight_id: Optional[str] = None,
                  **kwargs):
    comment = "[robotoff] Adding label tag '{}'".format(label_tag)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        'code': barcode,
        'add_labels': label_tag,
        'comment': comment,
    }
    update_product(params, **kwargs)


def add_brand(barcode: str, brand: str,
              insight_id: Optional[str] = None,
              **kwargs):
    comment = "[robotoff] Adding brand '{}'".format(brand)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        'code': barcode,
        'add_brands': brand,
        'comment': comment,
    }
    update_product(params, **kwargs)


def add_store(barcode: str, store: str,
              insight_id: Optional[str] = None,
              **kwargs):
    comment = "[robotoff] Adding store '{}'".format(store)

    if insight_id:
        comment += ", ID: {}".format(insight_id)

    params = {
        'code': barcode,
        'add_stores': store,
        'comment': comment,
    }
    update_product(params, **kwargs)


def update_product(params: Dict,
                   server_domain: Optional[str] = None,
                   session_cookie: Optional[str] = None):
    if server_domain is None:
        server_domain = settings.OFF_SERVER_DOMAIN

    url = get_product_update_url(server_domain)

    comment = params.get('comment')
    cookies = None
    if session_cookie:
        cookies = {
            'session': session_cookie,
        }
    else:
        params.update(AUTH_DICT)
        if comment:
            params['comment'] = comment + " (automated edit)"

    auth = None
    if server_domain.endswith('openfoodfacts.net'):
        # dev environment requires authentication
        auth = ('off', 'off')

    r = http_session.get(url, params=params,
                         auth=auth,
                         cookies=cookies)

    r.raise_for_status()
    json = r.json()

    status = json.get('status_verbose')

    if status != "fields saved":
        logger.warn(
            "Unexpected status during product update: {}".format(
                status))
