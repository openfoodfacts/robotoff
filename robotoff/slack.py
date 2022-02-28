import json
import operator
from typing import Dict, List, Optional

import requests

from robotoff import settings
from robotoff.insights.dataclass import InsightType
from robotoff.logo_label_type import LogoLabelType
from robotoff.models import LogoAnnotation, ProductInsight
from robotoff.prediction.types import Prediction
from robotoff.utils import get_logger, http_session
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


class SlackException(Exception):
    pass


class SlackNotifierInterface:
    """SlackNotifierInterface is an interface for posting Robotoff-related alerts and notifications to the OFF Slack channels."""

    def notify_image_flag(
        self, predictions: List[Prediction], source: str, barcode: str
    ):
        pass

    def notify_automatic_processing(self, insight: ProductInsight):
        pass

    def send_logo_notification(
        self, logo: LogoAnnotation, probs: Dict[LogoLabelType, float]
    ):
        pass


class NotifierFactory:
    """NotifierFactory is responsible for creating a notifier to post notifications to."""

    @staticmethod
    def get_notifier() -> SlackNotifierInterface:
        token = settings.slack_token()
        if token == "":
            return NoopSlackNotifier()
        return SlackNotifier(token)


def _sensitive_image(flag_type: str, flagged_label: str) -> bool:
    """Determines whether the given flagged image should be considered as sensitive."""
    is_human: bool = flagged_label in {
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
        "jaw",
        "nose",
        "facial expression",
        "glasses",
        "eyewear",
        "child",
        "baby",
        "human",
    }
    return (
        is_human and flag_type == "label_annotation"
    ) or flag_type == "safe_search_annotation"


def _slack_message_block(
    message_text: str, with_image: Optional[str] = None
) -> List[Dict]:
    """Formats given parameters into a Slack message block."""
    block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": message_text,
        },
    }

    if with_image:
        block["accessory"] = {
            "type": "image",
            "image_url": with_image,
            "alt_text": "-",
        }
    return [block]


class SlackNotifier(SlackNotifierInterface):
    """SlackNotifier implements the real SlackNotifier."""

    # Slack channel IDs.
    ROBOTOFF_ALERT_CHANNEL = "CGKPALRCG"
    ROBOTOFF_USER_ALERT_CHANNEL = "CGWSXDGSF"
    ROBOTOFF_PRIVATE_IMAGE_ALERT_CHANNEL = "GGMRWLEF2"
    ROBOTOFF_PUBLIC_IMAGE_ALERT_CHANNEL = "CT2N423PA"
    NUTRISCORE_ALERT_CHANNEL = "CJZNFCSNP"

    BASE_URL = "https://slack.com/api"
    POST_MESSAGE_URL = BASE_URL + "/chat.postMessage"

    NUTRISCORE_LABELS = {
        "en:nutriscore",
        "en:nutriscore-grade-a",
        "en:nutriscore-grade-b",
        "en:nutriscore-grade-c",
        "en:nutriscore-grade-d",
        "en:nutriscore-grade-e",
    }

    COLLAPSE_LINKS_PARAMS = {
        "unfurl_links": False,
        "unfurl_media": False,
    }

    def __init__(self, slack_token: str):
        """Should not be called directly, use the NotifierFactory instead."""
        self.slack_token = slack_token

    def notify_image_flag(
        self, predictions: List[Prediction], source_image: str, barcode: str
    ):
        """Sends alerts to Slack channels for flagged images."""
        if len(predictions) < 1:
            return

        text = ""
        slack_channel: str = self.ROBOTOFF_PUBLIC_IMAGE_ALERT_CHANNEL

        for flagged in predictions:
            flag_type = flagged.data["type"]
            label = flagged.data["label"]

            if _sensitive_image(flag_type, label):
                slack_channel = self.ROBOTOFF_PRIVATE_IMAGE_ALERT_CHANNEL

            if flag_type in ("safe_search_annotation", "label_annotation"):
                likelihood = flagged.data["likelihood"]
                text += f"type: {flag_type}\nlabel: *{label}*, score: {likelihood}\n"
            else:
                match_text = flagged.data["text"]
                text += f"type: {flag_type}\nlabel: *{label}*, match: {match_text}\n"

        edit_url = f"{settings.BaseURLProvider().get()}/cgi/product.pl?type=edit&code={barcode}"
        image_url = settings.OFF_IMAGE_BASE_URL + source_image

        full_text = f"{text}\n <{image_url}|Image> -- <{edit_url}|*Edit*>"
        message = _slack_message_block(full_text, with_image=image_url)

        self._post_message(message, slack_channel, **self.COLLAPSE_LINKS_PARAMS)

    def notify_automatic_processing(self, insight: ProductInsight):
        product_url = f"{settings.BaseURLProvider().get()}/product/{insight.barcode}"

        if insight.source_image:
            image_url = f"{settings.BaseURLProvider().static().get()}/images/products{insight.source_image}"
            metadata_text = f"(<{product_url}|product>, <{image_url}|source image>)"
        else:
            metadata_text = f"(<{product_url}|product>)"
        value = insight.value or insight.value_tag

        if insight.type in {
            InsightType.product_weight.name,
            InsightType.expiration_date.name,
        }:
            text = f"The {insight.type} `{value}` (match: `{insight.data['raw']}`) was automatically added to product {insight.barcode}"
        else:
            text = f"The `{value}` {insight.type} was automatically added to product {insight.barcode}"

        message = _slack_message_block(text + " " + metadata_text)

        if insight.value_tag in self.NUTRISCORE_LABELS:
            self._post_message(
                message, self.NUTRISCORE_ALERT_CHANNEL, **self.COLLAPSE_LINKS_PARAMS
            )
            return

        self._post_message(
            message, self.ROBOTOFF_ALERT_CHANNEL, **self.COLLAPSE_LINKS_PARAMS
        )

    def _get_base_params(self) -> JSONType:
        return {
            "username": "robotoff-bot",
            "token": self.slack_token,
            "icon_url": "https://s3-us-west-2.amazonaws.com/slack-files2/"
            "bot_icons/2019-03-01/565595869687_48.png",
        }

    def send_logo_notification(
        self, logo: LogoAnnotation, probs: Dict[LogoLabelType, float]
    ):
        crop_url = logo.get_crop_image_url()
        prob_text = "\n".join(
            (
                f"{label[0]} - {label[1]}: {prob:.2g}"
                for label, prob in sorted(
                    probs.items(), key=operator.itemgetter(1), reverse=True
                )
            )
        )
        barcode = logo.image_prediction.image.barcode
        base_off_url = settings.BaseURLProvider().get()
        text = (
            f"Prediction for <{crop_url}|image> "
            f"(<https://hunger.openfoodfacts.org/logos?logo_id={logo.id}|annotate logo>, "
            f"<{base_off_url}/product/{barcode}|product>):\n{prob_text}"
        )
        self._post_message(_slack_message_block(text), self.ROBOTOFF_ALERT_CHANNEL)

    def _post_message(
        self,
        blocks: List[Dict],
        channel: str,
        **kwargs,
    ):
        try:
            params: JSONType = {
                **(self._get_base_params()),
                "channel": channel,
                "blocks": json.dumps(blocks),
                **kwargs,
            }

            r = http_session.post(self.POST_MESSAGE_URL, data=params)
            response_json = _get_slack_json(r)
            return response_json
        except Exception as e:
            logger.error(
                "An exception occurred when sending a Slack " "notification", exc_info=e
            )


class NoopSlackNotifier(SlackNotifier):
    """NoopSlackNotifier is a NOOP SlackNotifier used in dev/local executions of Robotoff."""

    def __init__(self):
        super().__init__("")

    def _post_message(
        self,
        blocks: List[Dict],
        channel: str,
        **kwargs,
    ):
        """Overrides the actual posting to Slack with logging of the args that would've been posted."""
        logger.info(
            f"Alerting on slack channel '{channel}', with message:\n{blocks}\nand additional args:\n{kwargs}"
        )


def _get_slack_json(response: requests.Response) -> JSONType:
    json_data = response.json()

    if not response.ok:
        raise SlackException(
            "Non-200 status code from Slack: "
            "{}, response: {}"
            "".format(response.status_code, json_data)
        )

    if not json_data.get("ok", False):
        raise SlackException("Non-ok response: {}".format(json_data))

    return json_data
