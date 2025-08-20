import pytest

from robotoff import settings  # noqa: F401
from robotoff.types import ServerType  # noqa: F401


@pytest.mark.parametrize(
    "instance,got_url,want_url",
    [
        (
            "prod",
            "settings.BaseURLProvider.world(ServerType.off)",
            "https://world.openfoodfacts.org",
        ),
        (
            "prod",
            "settings.BaseURLProvider.world(ServerType.obf)",
            "https://world.openbeautyfacts.org",
        ),
        (
            "dev",
            "settings.BaseURLProvider.world(ServerType.opf)",
            "https://world.openproductfacts.net",
        ),
        (
            "prod",
            "settings.BaseURLProvider.robotoff()",
            "https://robotoff.openfoodfacts.org",
        ),
        (
            "prod",
            "settings.BaseURLProvider.country(ServerType.off, 'fr')",
            "https://fr.openfoodfacts.org",
        ),
        (
            "dev",
            "settings.BaseURLProvider.world(ServerType.off)",
            "https://world.openfoodfacts.net",
        ),
    ],
)
def test_base_url_provider(monkeypatch, instance, got_url, want_url):
    monkeypatch.setenv("ROBOTOFF_INSTANCE", instance)
    assert eval(got_url) == want_url
