from typing import Callable

import requests
from diskcache import Cache

from robotoff import settings

# Disk-cache to store any kind of content (but currently mostly images).
# It avoids having to download multiple times the same image from the server,
# with a reasonable disk usage (default to 1GB).
# diskcache Cache is thread-safe and process-safe, and every transaction is
# atomic. We can therefore define a single cache here and use it across the
# project.
disk_cache = Cache(settings.DISKCACHE_DIR)


def cache_http_request(
    key: str,
    cache: Cache,
    func: Callable[..., requests.Response | None],
    cache_expire: int | None = None,
    tag: str | None = None,
    *args,
    **kwargs,
) -> bytes | None:
    """Cache raw response (bytes) of HTTP requests.

    :param key: the cache key
    :param cache: the cache to use
    :param func: the function to call, must return a Request object
    :param cache_expire: expiration time of the item in the cache, defaults to
        None (no expiration)
    :param tag: a tag of the item in the cache (optional), defaults to None
    :return: the response bytes or None if an error occured while calling
      `func`
    """
    # Check if the item is already cached, and use it instead of sending
    # the HTTP request if it is
    content_bytes = cache.get(key)
    if content_bytes is None:
        r = func(*args, **kwargs)
        if r is None:
            # Don't save in cache if an error (or HTTP 404) occurred
            return None
        content_bytes = r.content
        # We store the raw byte content of the response in the cache
        disk_cache.set(key, r.content, expire=cache_expire, tag=tag)

    return content_bytes
