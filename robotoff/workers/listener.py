from multiprocessing.connection import Listener
from multiprocessing.pool import Pool
from typing import Dict

from robotoff import settings
from robotoff.utils import get_logger
from robotoff.workers.tasks import run_task

import sentry_sdk
from sentry_sdk import capture_exception

if settings.SENTRY_DSN:
    sentry_sdk.init(settings.SENTRY_DSN)


logger = get_logger()


def run():
    pool: Pool = Pool(settings.WORKER_COUNT)

    logger.info("Starting listener server on {}:{}"
                "".format(*settings.IPC_ADDRESS))
    logger.info("Starting listener server")

    with Listener(settings.IPC_ADDRESS,
                  authkey=settings.IPC_AUTHKEY,
                  family='AF_INET') as listener:
        while True:
            try:
                logger.info("Waiting for a connection...")

                with listener.accept() as conn:
                    event = conn.recv()
                    event_type: str = event['type']
                    logger.info("New '{}' event received".format(event_type))
                    event_kwargs: Dict = event.get('meta', {})

                    logger.info("Sending task to pool...")
                    pool.apply_async(run_task, (event_type, event_kwargs))
                    logger.info("Task sent")
            except Exception:
                capture_exception()
