import time

import pytest

from robotoff.utils.cache import cache_http_request, disk_cache


class FakeRequest:
    def __init__(self, content):
        self.content = content


class CallbackFunctions:
    get_bytes_called = False
    get_none_called = False
    get_bytes_with_expire_called = False

    # Test caching of a function that returns bytes
    @classmethod
    def get_bytes(cls):
        cls.get_bytes_called = True
        return FakeRequest(b"test bytes")

    # Test caching of a function that returns None
    @classmethod
    def get_none(cls):
        cls.get_none_called = True
        return None

    # Test caching with a custom cache expiration time
    @classmethod
    def get_bytes_with_expire(cls):
        cls.get_bytes_with_expire_called = True
        return FakeRequest(b"test bytes with expire")


@pytest.fixture
def clear_disk_cache():
    disk_cache.evict("unit_test")
    yield
    disk_cache.evict("unit_test")


def test_cache_http_request(clear_disk_cache):
    cached_bytes = cache_http_request(
        "test_key", cache=disk_cache, func=CallbackFunctions.get_bytes, tag="unit_test"
    )
    assert cached_bytes == b"test bytes"
    assert CallbackFunctions.get_bytes_called is True
    CallbackFunctions.get_bytes_called = False

    cache_http_request(
        key="test_key",
        cache=disk_cache,
        func=CallbackFunctions.get_bytes,
        tag="unit_test",
    )
    assert CallbackFunctions.get_bytes_called is False
    del disk_cache["test_key"]

    cached_none = cache_http_request(
        key="test_key_none",
        cache=disk_cache,
        func=CallbackFunctions.get_none,
        tag="unit_test",
    )
    assert cached_none is None

    cached_bytes_with_expire = cache_http_request(
        key="test_key_with_expire",
        cache=disk_cache,
        func=CallbackFunctions.get_bytes_with_expire,
        cache_expire=0.1,
        tag="unit_test",
    )
    assert cached_bytes_with_expire == b"test bytes with expire"
    assert CallbackFunctions.get_bytes_with_expire_called is True
    CallbackFunctions.get_bytes_with_expire_called = False

    # Wait for the cache to expire
    time.sleep(0.1)

    cached_bytes_with_expire = cache_http_request(
        key="test_key_with_expire",
        cache=disk_cache,
        func=CallbackFunctions.get_bytes_with_expire,
    )
    assert cached_bytes_with_expire == b"test bytes with expire"
    # Check that the function was called again
    assert CallbackFunctions.get_bytes_with_expire_called is True
    del disk_cache["test_key_with_expire"]
