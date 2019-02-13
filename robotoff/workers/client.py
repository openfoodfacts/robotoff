from multiprocessing.connection import Client
from typing import Dict

from robotoff import settings
from robotoff.utils import get_logger

logger = get_logger(__name__)


def send_ipc_event(event_type: str, meta: Dict = None):
    meta = meta or {}

    with Client(settings.IPC_ADDRESS, authkey=settings.IPC_AUTHKEY) as conn:
        logger.info("Sending event through IPC")
        conn.send({
            'type': event_type,
            'meta': meta,
        })
        logger.info("IPC event sent")
