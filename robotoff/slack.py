import operator
from typing import Any, Dict, List, Optional

import requests

from robotoff import settings
from robotoff.insights._enum import InsightType
from robotoff.insights.dataclass import RawInsight
from robotoff.logo_label_type import LogoLabelType
from robotoff.models import LogoAnnotation, ProductInsight
from robotoff.utils import get_logger, http_session
from robotoff.utils.types import JSONType

logger = get_logger(__name__)


class SlackException(Exception):
    pass


class SlackNotifierInterface:
    """SlackNotifierInterface is an interface for posting Robotoff-related alerts and notifications to the OFF Slack channels."""

    def notify_image_flag(self, insights: List[RawInsight], source: str, barcode: str):
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


class NoopSlackNotifier(SlackNotifierInterface):
    """NoopSlackNotifier is a NOOP SlackNotifier used in dev/local executions of Robotoff."""

    pass


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

    PRIVATE_MODERATION_LABELS = {
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

    def __init__(self, slack_token: str):
        """Should not be called directly, use the NotifierFactory instead."""
        self.slack_token = slack_token

    def notify_image_flag(self, insights: List[RawInsight], source: str, barcode: str):
        text = ""
        slack_channel: str = self.ROBOTOFF_PUBLIC_IMAGE_ALERT_CHANNEL

        for insight in insights:
            flag_type = insight.data["type"]
            label = insight.data["label"]

            if flag_type in ("safe_search_annotation", "label_annotation"):
                if (
                    flag_type == "label_annotation"
                    and label in self.PRIVATE_MODERATION_LABELS
                ) or flag_type == "safe_search_annotation":
                    slack_channel = self.ROBOTOFF_PRIVATE_IMAGE_ALERT_CHANNEL

                likelihood = insight.data["likelihood"]
                text += "type: {}, label: {}, score: {}\n".format(
                    flag_type, label, likelihood
                )
            else:
                match_text = insight.data["text"]
                text += "type: {}, label: {}, match: {}\n".format(
                    flag_type, label, match_text
                )

        url = settings.OFF_IMAGE_BASE_URL + source
        edit_url = "{}/cgi/product.pl?type=edit&code={}" "".format(
            settings.BaseURLProvider().get(), barcode
        )
        text += url + "\n"
        text += "edit: {}".format(edit_url)

        self._post_message(text, slack_channel)

    def notify_automatic_processing(self, insight: ProductInsight):
        product_url = "{}/product/{}".format(
            settings.BaseURLProvider().get(), insight.barcode
        )
        source_image = insight.source_image

        if source_image:
            image_url = (
                settings.BaseURLProvider().static() + "/images/products" + source_image
            )
            metadata_text = "(<{}|product>, <{}|source image>)".format(
                product_url, image_url
            )
        else:
            metadata_text = "(<{}|product>)".format(product_url)

        if insight.type == InsightType.label.name:
            text = "The `{}` label was automatically added to product {}" "".format(
                insight.value_tag, insight.barcode
            )

        elif insight.type == InsightType.product_weight.name:
            text = (
                "The weight `{}` (match: `{}`) was automatically added to "
                "product {}"
                "".format(insight.value, insight.data["raw"], insight.barcode)
            )

        elif insight.type == InsightType.packager_code.name:
            text = (
                "The `{}` packager code was automatically added to "
                "product {}".format(insight.value, insight.barcode)
            )

        elif insight.type == InsightType.expiration_date.name:
            text = (
                "The expiration date `{}` (match: `{}`) was automatically added to "
                "product {}".format(insight.value, insight.data["raw"], insight.barcode)
            )

        elif insight.type == InsightType.brand.name:
            text = "The `{}` brand was automatically added to " "product {}".format(
                insight.value, insight.barcode
            )

        elif insight.type == InsightType.store.name:
            text = "The `{}` store was automatically added to " "product {}".format(
                insight.value, insight.barcode
            )

        elif insight.type == InsightType.packaging.name:
            text = "The `{}` packaging was automatically added to " "product {}".format(
                insight.value_tag, insight.barcode
            )
        elif insight.type == InsightType.category.name:
            text = "The `{}` category was automatically added to " "product {}".format(
                insight.value_tag, insight.barcode
            )

        else:
            return

        text += " " + metadata_text
        slack_kwargs: Dict[str, Any] = {
            "unfurl_links": False,
            "unfurl_media": False,
        }
        if insight.value_tag in self.NUTRISCORE_LABELS:
            self._post_message(text, self.NUTRISCORE_ALERT_CHANNEL, **slack_kwargs)
            return

        self._post_message(text, self.ROBOTOFF_ALERT_CHANNEL, **slack_kwargs)

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
        self._post_message(text, self.ROBOTOFF_ALERT_CHANNEL)

    def _post_message(
        self,
        text: str,
        channel: str,
        attachments: Optional[List[JSONType]] = None,
        **kwargs,
    ):
        try:
            params: JSONType = {
                **(self._get_base_params()),
                "channel": channel,
                "text": text,
                **kwargs,
            }

            if attachments:
                params["attachments"] = attachments

            r = http_session.post(self.POST_MESSAGE_URL, data=params)
            response_json = _get_slack_json(r)
            return response_json
        except Exception as e:
            logger.error(
                "An exception occurred when sending a Slack " "notification", exc_info=e
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
