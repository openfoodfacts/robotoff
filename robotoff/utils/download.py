import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from diskcache import Cache
from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import SSLError, Timeout

from robotoff import settings
from robotoff.utils.cache import cache_http_request, disk_cache

from .logger import get_logger

logger = get_logger(__name__)


class AssetLoadingException(Exception):
    """Exception raised by `get_asset_from_url` when an asset cannot be fetched
    from URL or if loading failed.
    """

    pass


def get_asset_from_url(
    asset_url: str,
    error_raise: bool = True,
    session: Optional[requests.Session] = None,
) -> requests.Response | None:
    auth = (
        settings._off_net_auth
        if urlparse(asset_url).netloc.endswith("openfoodfacts.net")
        else None
    )
    try:
        if session:
            r = session.get(asset_url, auth=auth)
        else:
            r = requests.get(asset_url, auth=auth)
    except (RequestConnectionError, SSLError, Timeout) as e:
        error_message = "Cannot download %s"
        if error_raise:
            raise AssetLoadingException(error_message % asset_url) from e
        logger.info(error_message, asset_url, exc_info=e)
        return None

    if not r.ok:
        error_message = "Cannot download %s: HTTP %s"
        error_args = (asset_url, r.status_code)
        if error_raise:
            raise AssetLoadingException(error_message % error_args)
        logger.log(
            logging.INFO if r.status_code < 500 else logging.WARNING,
            error_message,
            *error_args,
        )
        return None

    return r


def cache_asset_from_url(
    key: str,
    cache: Cache | None = None,
    cache_expire: int | None = None,
    tag: str | None = None,
    *args,
    **kwargs,
) -> bytes | None:
    """Cache response on disk from `get_asset_from_url`.

    args and kwargs are passed to `get_asset_from_url`.

    :param key: the cache key
    :param url: the URL of the asset to fetch
    :param session: the requests session to use
    :param cache: the cache to use, defaults to Robotoff default cache
    :param cache_expire: expiration time of the item in the cache, defaults to
        None (no expiration)
    :param tag: a tag of the item in the cache (optional), defaults to None
    :return: the response bytes or None if an error occured while calling
      `func`
    """
    cache = cache or disk_cache
    return cache_http_request(
        key,
        cache,
        get_asset_from_url,
        cache_expire,
        tag,
        *args,
        **kwargs,
    )
