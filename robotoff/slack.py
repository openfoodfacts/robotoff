from typing import List, Optional

import requests

from robotoff import settings
from robotoff.insights._enum import InsightType
from robotoff.models import ProductInsight
from robotoff.utils import get_logger
from robotoff.utils.types import JSONType

http_session = requests.Session()

BASE_URL = "https://slack.com/api"
POST_MESSAGE_URL = BASE_URL + "/chat.postMessage"
NUTRISCORE_LABELS = {
    "en:nutriscore",
    "en:nutriscore-a",
    "en:nutriscore-b",
    "en:nutriscore-c",
    "en:nutriscore-d",
    "en:nutriscore-e",
}

logger = get_logger(__name__)


class SlackException(Exception):
    pass


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


def notify_image_flag(insights: List[JSONType], source: str, barcode: str):
    text = ""
    slack_channel: str = settings.SLACK_OFF_ROBOTOFF_PUBLIC_IMAGE_ALERT_CHANNEL

    for insight in insights:
        flag_type = insight["type"]
        label = insight["label"]

        if flag_type in ("safe_search_annotation", "label_annotation"):
            if (
                flag_type == "label_annotation" and label in PRIVATE_MODERATION_LABELS
            ) or flag_type == "safe_search_annotation":
                slack_channel = settings.SLACK_OFF_ROBOTOFF_PRIVATE_IMAGE_ALERT_CHANNEL

            likelihood = insight["likelihood"]
            text += "type: {}, label: {}, score: {}\n".format(
                flag_type, label, likelihood
            )
        else:
            match_text = insight["text"]
            text += "type: {}, label: {}, match: {}\n".format(
                flag_type, label, match_text
            )
            if "moved" in insight:
                text += "Product moved to {}\n".format(insight["moved"])

    url = settings.OFF_IMAGE_BASE_URL + source
    edit_url = "{}/cgi/product.pl?type=edit&code={}" "".format(
        settings.OFF_BASE_WEBSITE_URL, barcode
    )
    text += url + "\n"
    text += "edit: {}".format(edit_url)

    post_message(text, slack_channel)


def notify_automatic_processing(insight: ProductInsight):
    product_url = "{}/product/{}".format(settings.OFF_BASE_WEBSITE_URL, insight.barcode)
    source_image = insight.source_image

    if source_image:
        image_url = "https://static.openfoodfacts.org/images/products" + source_image
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
            "".format(insight.data["text"], insight.data["raw"], insight.barcode)
        )

    elif insight.type == InsightType.packager_code.name:
        text = "The `{}` packager code was automatically added to " "product {}".format(
            insight.data["text"], insight.barcode
        )

    elif insight.type == InsightType.expiration_date.name:
        text = (
            "The expiration date `{}` (match: `{}`) was automatically added to "
            "product {}".format(
                insight.data["text"], insight.data["raw"], insight.barcode
            )
        )

    elif insight.type == InsightType.brand.name:
        text = "The `{}` brand was automatically added to " "product {}".format(
            insight.value, insight.barcode
        )

    elif insight.type == InsightType.store.name:
        text = "The `{}` store was automatically added to " "product {}".format(
            insight.data["store"], insight.barcode
        )

    elif insight.type == InsightType.packaging.name:
        text = "The `{}` packaging was automatically added to " "product {}".format(
            insight.value_tag, insight.barcode
        )

    else:
        return

    text += " " + metadata_text
    slack_kwargs = {
        "unfurl_links": False,
        "unfurl_media": False,
    }
    if insight.value_tag in NUTRISCORE_LABELS:
        post_message(text, settings.SLACK_OFF_NUTRISCORE_ALERT_CHANNEL, **slack_kwargs)
        return

    post_message(text, settings.SLACK_OFF_ROBOTOFF_ALERT_CHANNEL, **slack_kwargs)


def get_base_params() -> JSONType:
    return {
        "username": "robotoff-bot",
        "token": settings.SLACK_TOKEN,
        "icon_url": "https://s3-us-west-2.amazonaws.com/slack-files2/"
        "bot_icons/2019-03-01/565595869687_48.png",
    }


def raise_if_slack_token_undefined():
    if settings.SLACK_TOKEN is None:
        raise ValueError(
            "The bot Slack token must be passed in the SLACK_"
            "TOKEN environment variable"
        )


def post_message(
    text: str, channel: str, attachments: Optional[List[JSONType]] = None, **kwargs
):
    try:
        _post_message(text, channel, attachments, **kwargs)
    except Exception as e:
        logger.error(
            "An exception occurred when sending a Slack " "notification", exc_info=e
        )


def _post_message(
    text: str, channel: str, attachments: Optional[List[JSONType]] = None, **kwargs
):
    raise_if_slack_token_undefined()
    params: JSONType = {**get_base_params(), "channel": channel, "text": text, **kwargs}

    if attachments:
        params["attachments"] = attachments

    r = http_session.post(POST_MESSAGE_URL, data=params)
    response_json = get_slack_json(r)
    return response_json


def get_slack_json(response: requests.Response) -> JSONType:
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
