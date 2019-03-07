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


logger = get_logger(__name__)


class SlackException(Exception):
    pass


def notify_image_flag(insights: List[JSONType], source: str, barcode: str):
    flags = ", ".join(["{} ({})".format(i['type'], i['likelihood'])
                       for i in insights])
    url = "{}/{}".format(settings.OFF_IMAGE_BASE_URL,
                         source)
    edit_url = "{}/cgi/product.pl?type=edit&code={}" \
               "".format(settings.OFF_BASE_WEBSITE_URL, barcode)
    text = ("Image flagged as {}: {}\nedit: {}".format(
        flags, url, edit_url))
    post_message(text, settings.SLACK_OFF_ROBOTOFF_IMAGE_ALERT_CHANNEL)


def notify_automatic_processing(insight: ProductInsight):
    if insight.type == InsightType.label.name:
        text = ("The `{}` label was automatically added to product {}/product"
                "/{}".format(insight.value_tag,
                             settings.OFF_BASE_WEBSITE_URL,
                             insight.barcode))
        post_message(text, settings.SLACK_OFF_ROBOTOFF_ALERT_CHANNEL)

        if insight.value_tag == 'en:nutriscore':
            post_message(text, settings.SLACK_OFF_NUTRISCORE_ALERT_CHANNEL)

    elif insight.type == InsightType.product_weight.name:
        text = ("The weight `{}` was automatically added to product {}/product"
                "/{}".format(insight.data['text'],
                             settings.OFF_BASE_WEBSITE_URL,
                             insight.barcode))
        post_message(text, settings.SLACK_OFF_ROBOTOFF_ALERT_CHANNEL)
    else:
        return


def notify_batch_processing(batch_size: int):
        text = "{} additional insights were automatically " \
               "applied".format(batch_size)
        post_message(text, settings.SLACK_OFF_ROBOTOFF_ALERT_CHANNEL)


def get_base_params() -> JSONType:
    return {
        'username': "robotoff-bot",
        'token': settings.SLACK_TOKEN,
        'icon_url': "https://s3-us-west-2.amazonaws.com/slack-files2/"
                    "bot_icons/2019-03-01/565595869687_48.png",
    }


def raise_if_slack_token_undefined():
    if settings.SLACK_TOKEN is None:
        raise ValueError("The bot Slack token must be passed in the SLACK_"
                         "TOKEN environment variable")


def post_message(text: str,
                 channel: str,
                 attachments: Optional[List[JSONType]] = None):
    try:
        _post_message(text, channel, attachments)
    except Exception as e:
        logger.error("An exception occurred when sending a Slack "
                     "notification", exc_info=e)


def _post_message(text: str,
                  channel: str,
                  attachments: Optional[List[JSONType]] = None):
    raise_if_slack_token_undefined()
    params: JSONType = {
        **get_base_params(),
        'channel': channel,
        'text': text,
    }

    if attachments:
        params['attachments'] = attachments

    r = http_session.post(POST_MESSAGE_URL, data=params)
    response_json = get_slack_json(r)
    return response_json


def get_slack_json(response: requests.Response) -> JSONType:
    json_data = response.json()

    if not response.ok:
        raise SlackException("Non-200 status code from Slack: "
                             "{}, response: {}"
                             "".format(response.status_code,
                                       json_data))

    if not json_data.get('ok', False):
        raise SlackException("Non-ok response: {}".format(json_data))

    return json_data
