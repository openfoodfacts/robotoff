import json
import logging
from typing import Optional

import pytest

from robotoff import settings, slack
from robotoff.models import ImageModel, ImagePrediction, LogoAnnotation, ProductInsight
from robotoff.types import Prediction, PredictionType, ProductIdentifier, ServerType

DEFAULT_BARCODE = "123"
DEFAULT_SERVER_TYPE = ServerType.off
DEFAULT_PRODUCT_ID = ProductIdentifier(DEFAULT_BARCODE, DEFAULT_SERVER_TYPE)


class MockSlackResponse:
    def __init__(self):
        self.json_data = {"ok": True}
        self.status_code = 200
        self.ok = True

    def json(self):
        return self.json_data


class PartialRequestMatcher:
    def __init__(
        self, expected_text: str, slack_channel: str, image_url: Optional[str] = None
    ):
        self.expected_text = expected_text
        self.expected_channel = slack_channel
        self.expected_image_url = image_url

    def __eq__(self, actual):
        assert self.expected_channel == actual["channel"]

        act_blocks = json.loads(actual["blocks"])

        assert len(act_blocks) == 1
        assert act_blocks[0]["text"]["text"] == self.expected_text
        if self.expected_image_url:
            assert act_blocks[0]["accessory"]["image_url"] == self.expected_image_url
        else:
            assert "accessory" not in act_blocks[0]

        return True


@pytest.mark.parametrize(
    "token_value, moderation_url, want_type",
    [
        ("T", "", slack.SlackNotifier),
        ("T", "http://test.org/", slack.MultiNotifier),
        ("", "", slack.NoopSlackNotifier),
    ],
)
def test_notifier_factory(monkeypatch, token_value, moderation_url, want_type):
    monkeypatch.setattr(settings, "slack_token", lambda: token_value)
    monkeypatch.setattr(settings, "IMAGE_MODERATION_SERVICE_URL", moderation_url)
    notifier = slack.NotifierFactory.get_notifier()
    assert type(notifier) is want_type


def test_notify_image_flag_no_prediction(mocker):
    mock = mocker.patch("robotoff.slack.http_session.post")

    notifier = slack.MultiNotifier(
        [slack.SlackNotifier(""), slack.ImageModerationNotifier("")]
    )
    # no predictions associated to image
    notifier.notify_image_flag(
        [],
        "/source_image",
        DEFAULT_PRODUCT_ID,
    )
    # wont publish anything
    assert not mock.called


def test_notify_image_flag_public(mocker, monkeypatch):
    """Test notifying a potentially sensitive public image"""
    mock_slack = mocker.patch(
        "robotoff.slack.http_session.post", return_value=MockSlackResponse()
    )
    mock_image_moderation = mocker.patch(
        "robotoff.slack.http_session.put", return_value=MockSlackResponse()
    )
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply

    slack_notifier = slack.SlackNotifier("")
    notifier = slack.MultiNotifier(
        [slack_notifier, slack.ImageModerationNotifier("http://images.org/")]
    )

    notifier.notify_image_flag(
        [
            Prediction(
                type=PredictionType.image_flag,
                data={"text": "bad_word", "type": "SENSITIVE", "label": "flagged"},
            )
        ],
        "/source_image/2.jpg",
        DEFAULT_PRODUCT_ID,
    )

    mock_slack.assert_called_once_with(
        slack_notifier.POST_MESSAGE_URL,
        data=PartialRequestMatcher(
            f"type: SENSITIVE\nlabel: *flagged*, match: bad_word\n\n <{settings.BaseURLProvider.image_url(DEFAULT_SERVER_TYPE, '/source_image/2.jpg')}|Image> -- <{settings.BaseURLProvider.world(DEFAULT_SERVER_TYPE)}/cgi/product.pl?type=edit&code=123|*Edit*>",
            slack_notifier.ROBOTOFF_PUBLIC_IMAGE_ALERT_CHANNEL,
            settings.BaseURLProvider.image_url(
                DEFAULT_SERVER_TYPE, "/source_image/2.jpg"
            ),
        ),
    )
    mock_image_moderation.assert_called_once_with(
        "http://images.org/123",
        data={
            "imgid": 2,
            "url": settings.BaseURLProvider.image_url(
                DEFAULT_SERVER_TYPE, "/source_image/2.jpg"
            ),
        },
    )


def test_notify_image_flag_private(mocker, monkeypatch):
    """Test notifying a potentially sensitive private image"""
    mock_slack = mocker.patch(
        "robotoff.slack.http_session.post", return_value=MockSlackResponse()
    )
    mock_image_moderation = mocker.patch(
        "robotoff.slack.http_session.put", return_value=MockSlackResponse()
    )
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply

    slack_notifier = slack.SlackNotifier("")
    notifier = slack.MultiNotifier(
        [slack_notifier, slack.ImageModerationNotifier("http://images.org/")]
    )

    notifier.notify_image_flag(
        [
            Prediction(
                type=PredictionType.image_flag,
                data={"type": "label_annotation", "label": "face", "likelihood": 0.8},
            )
        ],
        "/source_image/2.jpg",
        DEFAULT_PRODUCT_ID,
    )

    mock_slack.assert_called_once_with(
        slack_notifier.POST_MESSAGE_URL,
        data=PartialRequestMatcher(
            f"type: label_annotation\nlabel: *face*, score: 0.8\n\n <{settings.BaseURLProvider.image_url(DEFAULT_SERVER_TYPE, '/source_image/2.jpg')}|Image> -- <{settings.BaseURLProvider.world(DEFAULT_SERVER_TYPE)}/cgi/product.pl?type=edit&code=123|*Edit*>",
            slack_notifier.ROBOTOFF_PRIVATE_IMAGE_ALERT_CHANNEL,
            settings.BaseURLProvider.image_url(
                DEFAULT_SERVER_TYPE, "/source_image/2.jpg"
            ),
        ),
    )
    mock_image_moderation.assert_called_once_with(
        "http://images.org/123",
        data={
            "imgid": 2,
            "url": settings.BaseURLProvider.image_url(
                DEFAULT_SERVER_TYPE, "/source_image/2.jpg"
            ),
        },
    )


def test_notify_automatic_processing_weight(mocker, monkeypatch):
    mock = mocker.patch(
        "robotoff.slack.http_session.post", return_value=MockSlackResponse()
    )
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply

    notifier = slack.SlackNotifier("")

    print(settings.BaseURLProvider.image_url(DEFAULT_SERVER_TYPE, "/image/1"))
    notifier.notify_automatic_processing(
        ProductInsight(
            barcode=DEFAULT_BARCODE,
            source_image="/image/1",
            type="weight",
            value="200g",
            data={"raw": "en:200g"},
            server_type=DEFAULT_SERVER_TYPE,
        )
    )

    mock.assert_called_once_with(
        notifier.POST_MESSAGE_URL,
        data=PartialRequestMatcher(
            f"The `200g` weight was automatically added to product 123 (<{settings.BaseURLProvider.world(DEFAULT_SERVER_TYPE)}/product/123|product>, <{settings.BaseURLProvider.image_url(DEFAULT_SERVER_TYPE, '/image/1')}|source image>)",
            notifier.ROBOTOFF_ALERT_CHANNEL,
        ),
    )


def test_notify_automatic_processing_label(mocker, monkeypatch):
    mock = mocker.patch(
        "robotoff.slack.http_session.post", return_value=MockSlackResponse()
    )
    monkeypatch.delenv("ROBOTOFF_SCHEME", raising=False)  # force defaults to apply

    notifier = slack.SlackNotifier("")

    notifier.notify_automatic_processing(
        ProductInsight(
            barcode=DEFAULT_BARCODE,
            source_image="/image/1",
            type="label",
            value_tag="en:vegan",
            server_type=DEFAULT_SERVER_TYPE,
        )
    )

    mock.assert_called_once_with(
        notifier.POST_MESSAGE_URL,
        data=PartialRequestMatcher(
            f"The `en:vegan` label was automatically added to product 123 (<{settings.BaseURLProvider.world(DEFAULT_SERVER_TYPE)}/product/123|product>, <{settings.BaseURLProvider.image_url(DEFAULT_SERVER_TYPE, '/image/1')}|source image>)",
            notifier.ROBOTOFF_ALERT_CHANNEL,
        ),
    )


def test_noop_slack_notifier_logging(caplog):
    caplog.set_level(logging.INFO)
    notifier = slack.NoopSlackNotifier()

    notifier.send_logo_notification(
        LogoAnnotation(
            image_prediction=ImagePrediction(
                image=ImageModel(
                    barcode=DEFAULT_BARCODE,
                    source_image="/123/1.jpg",
                    width=10,
                    height=10,
                    server_type=DEFAULT_SERVER_TYPE.name,
                ),
            ),
            bounding_box=(1, 1, 2, 2),
            barcode=DEFAULT_BARCODE,
            source_image="/123/1.jpg",
        ),
        {},
    )

    (logged,) = caplog.records
    assert logged.msg.startswith("Alerting on slack channel")
