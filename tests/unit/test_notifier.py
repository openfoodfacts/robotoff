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
    monkeypatch.setattr(settings, "IMAGE_MODERATION_SERVICE_URL", moderation_url)
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


def test_notify_image_flag_public(mocker, monkeypatch):
    """Test notifying a potentially sensitive public image"""
    mock_http = mocker.patch("robotoff.notifier.http_session.post")
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
    mock_http.assert_any_call(
        "https://images.org",
        json={
            "barcode": "123",
            "type": "image",
            "url": "https://images.openfoodfacts.net/images/products/source_image/2.jpg",
            "user_id": "roboto-app",
            "source": "robotoff",
            "confidence": None,
            "image_id": "2",
            "flavor": "off",
            "reason": "other",
            "comment": "Robotoff detection: 'bad_word' (flagged)",
        },
    )


def test_notify_image_flag_private(mocker, monkeypatch):
    """Test notifying a potentially sensitive private image"""
    mock_http = mocker.patch("robotoff.notifier.http_session.post")
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
    mock_http.assert_any_call(
        "https://images.org",
        json={
            "barcode": "123",
            "type": "image",
            "url": "https://images.openfoodfacts.net/images/products/source_image/2.jpg",
            "user_id": "roboto-app",
            "source": "robotoff",
            "image_id": "2",
            "flavor": "off",
            "reason": "human",
            "comment": "Robotoff detection: face",
            "confidence": 0.8,
        },
    )
