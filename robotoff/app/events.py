from multiprocessing import Process, SimpleQueue
from typing import Optional

import requests

from robotoff import settings
from robotoff.utils import get_logger

logger = get_logger(__name__)


class EventProcessor:
    """Send events in an outside process"""

    # the process and queue to send events
    process = None
    queue = None

    def get(self):
        """Start a process to handle events, but only when needed,
        and return communication pipe
        """
        if self.process is None:
            self.queue = SimpleQueue()
            # Create a daemonic process
            self.process = Process(target=send_events, args=(self.queue,), daemon=True)
            self.process.start()
        return self.queue

    def send_async(self, *args, **kwargs):
        if settings.EVENTS_API_URL:
            queue = self.get()
            queue.put((settings.EVENTS_API_URL, args, kwargs))


# a singleton for event processor
event_processor = EventProcessor()


def send_events(queue):
    """Loop to send events in a specific process"""
    while True:
        api_url, args, kwargs = queue.get()
        send_event(api_url, *args, **kwargs)


def send_event(
    api_url: str,
    event_type: str,
    user_id: str,
    device_id: str,
    barcode: Optional[str] = None,
):
    event = {
        "event_type": event_type,
        "user_id": user_id,
        "device_id": device_id,
        "barcode": barcode,
    }
    logger.debug("Event: %s", event)
    response = requests.post(api_url, json=event)
    logger.debug("Event API response: %s", response)
    return response
