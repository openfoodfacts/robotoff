import pytest

from robotoff import settings


@pytest.mark.parametrize(
    "instance,got_url,want_url",
    [
        ("prod", "settings.BaseURLProvider().get()", "https://world.openfoodfacts.org"),
        (
            "prod",
            "settings.BaseURLProvider().robotoff().get()",
            "https://robotoff.openfoodfacts.org",
        ),
        (
            "prod",
            "settings.BaseURLProvider().country('fr').get()",
            "https://fr.openfoodfacts.org",
        ),
        # In cases where multiple overrides are called, the last one takes precedence.
        (
            "prod",
            "settings.BaseURLProvider().country('fr').robotoff().get()",
            "https://robotoff.openfoodfacts.org",
        ),
        ("dev", "settings.BaseURLProvider().get()", "https://world.openfoodfacts.net"),
    ],
)
def test_base_url_provider(monkeypatch, instance, got_url, want_url):
    monkeypatch.setattr(settings, "_robotoff_instance", instance)
    monkeypatch.delenv("ROBOTOFF_DOMAIN", raising=False)  # force defaults to apply
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply
    assert eval(got_url) == want_url


def test_slack_token_valid_prod(monkeypatch):
    monkeypatch.setattr(settings, "_robotoff_instance", "prod")
    monkeypatch.setattr(settings, "_slack_token", "TEST_TOKEN")
    assert settings.slack_token() == "TEST_TOKEN"


def test_slack_token_valid_dev(monkeypatch):
    monkeypatch.setattr(settings, "_robotoff_instance", "dev")
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
    monkeypatch.setattr(settings, "_robotoff_instance", instance)
    monkeypatch.setattr(settings, "_slack_token", token)
    with pytest.raises(ValueError):
        settings.slack_token()
