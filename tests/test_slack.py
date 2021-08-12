import pytest

from robotoff import settings, slack


@pytest.mark.parametrize(
    "token_value,want_type",
    [
        ("T", slack.SlackNotifier),
        ("", slack.NoopSlackNotifier),
    ],
)
def test_notifier_factory(monkeypatch, token_value, want_type):
    def test_slack_token(t: str) -> str:
        return t

    monkeypatch.setattr(settings, "slack_token", lambda: test_slack_token(token_value))
    notifier = slack.NotifierFactory.get_notifier()
    assert type(notifier) is want_type
