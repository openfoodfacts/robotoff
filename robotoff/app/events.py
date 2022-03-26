from multiprocessing import Process

import requests

from robotoff.settings import EVENTS_API_URL
from robotoff.utils import get_logger

logger = get_logger(__name__)


def send_event(event_type: str, user_id: str, device_id: str, barcode: str = None):
    event = {
        "event_type": event_type,
        "user_id": user_id,
        "device_id": device_id,
        "barcode": barcode,
    }
    logger.debug(f"Event: {event}")
    response = requests.post(EVENTS_API_URL, json=event)
    logger.debug(f"Event API response: {response}")
    return response


def send_event_async(*args, **kwargs):
    process = Process(
        target=send_event, args=args, kwargs=kwargs, daemon=True
    )  # Create a daemonic process
    process.start()
