import pytest

from robotoff import settings
from robotoff.notifier import ImageModerationNotifier, MultiNotifier, NotifierFactory
from robotoff.types import Prediction, PredictionType, ProductIdentifier, ServerType

DEFAULT_BARCODE = "123"
DEFAULT_SERVER_TYPE = ServerType.off
DEFAULT_PRODUCT_ID = ProductIdentifier(DEFAULT_BARCODE, DEFAULT_SERVER_TYPE)


@pytest.mark.parametrize(
    "moderation_url, want_type",
    [("http://test.org/", ImageModerationNotifier)],
)
def test_notifier_factory(monkeypatch, moderation_url, want_type):
    notifier = NotifierFactory.get_notifier()
    assert type(notifier) is want_type


def test_notify_image_flag_no_prediction(mocker):
    mock = mocker.patch("robotoff.notifier.http_session.post")

    notifier = MultiNotifier([ImageModerationNotifier("")])
    # no predictions associated to image
    notifier.notify_image_flag(
        [],
        "/source_image",
        DEFAULT_PRODUCT_ID,
    )
    # wont publish anything
    assert not mock.called


def test_notify_image_flag_public(mocker):
    """Test notifying a potentially sensitive public image"""
    mock_http = mocker.patch("robotoff.notifier.http_session.post")
    mocker.patch.object(settings, "IMAGE_MODERATION_SERVICE_TOKEN", "test_token_123")
    notifier = MultiNotifier([ImageModerationNotifier("https://images.org")])

    notifier.notify_image_flag(
        [
            Prediction(
                type=PredictionType.image_flag,
                data={"text": "bad_word", "type": "text", "label": "flagged"},
            )
        ],
        "/source_image/2.jpg",
        DEFAULT_PRODUCT_ID,
    )

    assert len(mock_http.mock_calls) == 1
    json = mock_http.call_args.kwargs["json"]
    headers = mock_http.call_args.kwargs["headers"]
    assert json["barcode"] == "123"
    assert json["image_id"] == "2"
    assert json["comment"] == "Robotoff detection: 'bad_word' (flagged)"
    assert json["reason"] == "other"
    assert json["confidence"] is None
    assert (
        json["url"]
        == "https://images.openfoodfacts.net/images/products/source_image/2.jpg"
    )
    assert json["user_id"] == "roboto-app"
    assert json["source"] == "robotoff"
    assert json["type"] == "image"
    assert json["flavor"] == "off"
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test_token_123"
    mock_http.assert_any_call(
        "https://images.org",
        json=json,
        headers=mocker.ANY,
    )


def test_notify_image_flag_private(mocker, monkeypatch):
    """Test notifying a potentially sensitive private image"""
    mock_http = mocker.patch("robotoff.notifier.http_session.post")
    mocker.patch.object(settings, "IMAGE_MODERATION_SERVICE_TOKEN", "test_token_123")
    notifier = MultiNotifier([ImageModerationNotifier("https://images.org")])

    notifier.notify_image_flag(
        [
            Prediction(
                type=PredictionType.image_flag,
                data={"type": "label_annotation", "label": "face", "likelihood": 0.8},
                confidence=0.8,
            )
        ],
        "/source_image/2.jpg",
        DEFAULT_PRODUCT_ID,
    )

    assert len(mock_http.mock_calls) == 1
    json = mock_http.call_args.kwargs["json"]
    headers = mock_http.call_args.kwargs["headers"]
    assert json["barcode"] == "123"
    assert json["image_id"] == "2"
    assert json["comment"] == "Robotoff detection: face"
    assert json["reason"] == "human"
    assert json["confidence"] == 0.8
    assert (
        json["url"]
        == "https://images.openfoodfacts.net/images/products/source_image/2.jpg"
    )
    assert json["user_id"] == "roboto-app"
    assert json["source"] == "robotoff"
    assert json["type"] == "image"
    assert json["flavor"] == "off"
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test_token_123"
    mock_http.assert_any_call(
        "https://images.org",
        json=json,
        headers=mocker.ANY,
    )
