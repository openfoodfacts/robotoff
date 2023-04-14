import pytest

from robotoff import settings
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
    monkeypatch.delenv("ROBOTOFF_TLD", raising=False)  # force defaults to apply
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply
    assert eval(got_url) == want_url


def test_slack_token_valid_prod(monkeypatch):
    monkeypatch.setenv("ROBOTOFF_INSTANCE", "prod")
    monkeypatch.setattr(settings, "_slack_token", "TEST_TOKEN")
    assert settings.slack_token() == "TEST_TOKEN"


def test_slack_token_valid_dev(monkeypatch):
    monkeypatch.setenv("ROBOTOFF_INSTANCE", "dev")
    monkeypatch.setattr(settings, "_slack_token", "")
    assert settings.slack_token() == ""


@pytest.mark.parametrize(
    "instance,token",
    [
        ("prod", ""),
        ("dev", "TEST_TOKEN"),
    ],
)
def test_slack_token_errors(monkeypatch, instance, token):
    monkeypatch.setenv("ROBOTOFF_INSTANCE", instance)
    monkeypatch.setattr(settings, "_slack_token", token)
    with pytest.raises(ValueError):
        settings.slack_token()
