from robotoff import settings
from robotoff.types import Prediction, ProductIdentifier
from robotoff.utils import get_logger, http_session

logger = get_logger(__name__)


class NotifierInterface:
    """NotifierInterface is an interface for sending notifications
    to external services."""

    # Note: we do not use abstract methods,
    # for a notifier might choose to only implements a few

    def notify_image_flag(
        self,
        predictions: list[Prediction],
        source_image: str,
        product_id: ProductIdentifier,
    ):
        pass


class NotifierFactory:
    """NotifierFactory is responsible for creating a notifier to post
    notifications to."""

    @staticmethod
    def get_notifier() -> NotifierInterface:
        notifiers: list[NotifierInterface] = []
        moderation_service_url: str | None = settings.IMAGE_MODERATION_SERVICE_URL
        if moderation_service_url:
            notifiers.append(ImageModerationNotifier(moderation_service_url))
        if len(notifiers) == 1:
            return notifiers[0]
        else:
            return MultiNotifier(notifiers)


HUMAN_FLAG_LABELS = {
    "face",
    "head",
    "selfie",
    "hair",
    "forehead",
    "chin",
    "cheek",
    "tooth",
    "eyebrow",
    "ear",
    "neck",
    "nose",
    "facial expression",
    "child",
    "baby",
    "human",
}


class MultiNotifier(NotifierInterface):
    """Aggregate multiple notifiers in one instance

    See NotifierInterface for methods documentation

    :param notifiers: the notifiers to dispatch to
    """

    def __init__(self, notifiers: list[NotifierInterface]):
        self.notifiers: list[NotifierInterface] = notifiers

    def _dispatch(self, function_name: str, *args, **kwargs):
        """dispatch call to function_name to all notifiers"""
        for notifier in self.notifiers:
            fn = getattr(notifier, function_name)
            fn(*args, **kwargs)

    def notify_image_flag(
        self,
        predictions: list[Prediction],
        source_image: str,
        product_id: ProductIdentifier,
    ):
        self._dispatch("notify_image_flag", predictions, source_image, product_id)


class ImageModerationNotifier(NotifierInterface):
    """Notifier to dispatch to image moderation server

    :param service_url: base url for image moderation service
    """

    def __init__(self, service_url):
        self.service_url = service_url.rstrip("/")
        self.token = settings.IMAGE_MODERATION_SERVICE_TOKEN

    def notify_image_flag(
        self,
        predictions: list[Prediction],
        source_image: str,
        product_id: ProductIdentifier,
    ):
        """Send image to the moderation server so that a human can moderate
        it"""
        if not predictions:
            return

        image_url = settings.BaseURLProvider.image_url(
            product_id.server_type, source_image
        )
        image_id = source_image.rsplit("/", 1)[-1].split(".", 1)[0]
        for prediction in predictions:
            reason = "other"
            prediction_subtype = prediction.data.get("type")
            prediction_label = prediction.data.get("label")
            if prediction_subtype == "safe_search_annotation":
                reason = "inappropriate"
            elif (
                prediction_subtype == "label_annotation"
                and prediction_label in HUMAN_FLAG_LABELS
            ):
                reason = "human"
            elif prediction_subtype == "face_annotation":
                reason = "human"
            elif prediction_subtype == "text" and prediction_label == "beauty":
                # Don't send beauty text detection to moderation service for
                # now
                continue

            if "label" in prediction.data:
                if prediction_subtype == "text":
                    comment = f"Robotoff detection: '{prediction.data['text']}' ({prediction.data['label']})"
                else:
                    comment = f"Robotoff detection: {prediction.data['label']}"
            else:
                comment = "Robotoff detection"

            data = {
                "barcode": product_id.barcode,
                "type": "image",
                "url": image_url,
                "user_id": "roboto-app",
                "source": "robotoff",
                "confidence": prediction.confidence,
                "image_id": image_id,
                "flavor": product_id.server_type.value,
                "reason": reason,
                "comment": comment,
            }
            headers = {
                "Authorization": f"Bearer {self.token}"
            }
            try:
                logger.info("Notifying image %s to moderation service", image_url)
                http_session.post(self.service_url, json=data, headers=headers)
            except Exception:
                logger.exception(
                    "Error while notifying image to moderation service",
                    extra={
                        "params": data,
                        "url": image_url,
                        "barcode": product_id.barcode,
                    },
                )
