import pytest

from robotoff.settings import BaseURLProvider


@pytest.mark.parametrize(
    "got_url,want_url",
    [
        (BaseURLProvider().get(), "https://world.openfoodfacts.org"),
        (BaseURLProvider().robotoff().get(), "https://robotoff.openfoodfacts.org"),
        (BaseURLProvider().country("fr").get(), "https://fr.openfoodfacts.org"),
        # In cases where multiple overrides are called, the last one takes precedence.
        (
            BaseURLProvider().country("fr").robotoff().get(),
            "https://robotoff.openfoodfacts.org",
        ),
    ],
)
def test_base_url_provider(got_url, want_url):
    assert got_url == want_url
