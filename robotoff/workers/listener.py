from multiprocessing.connection import Listener
from multiprocessing.pool import Pool
from typing import Dict

from robotoff import settings
from robotoff.utils import get_logger
from robotoff.workers.tasks import run_task

logger = get_logger()


def run():
    pool: Pool = Pool(settings.WORKER_COUNT)

    logger.info("Starting listener server")

    with Listener(settings.IPC_ADDRESS, authkey=settings.IPC_AUTHKEY) as listener:
        while True:
            logger.info("Waiting for a connection...")

            with listener.accept() as conn:
                event = conn.recv()
                event_type: str = event['type']
                logger.info("New '{}' event received".format(event_type))
                event_kwargs: Dict = event.get('meta', {})

                logger.info("Sending task to pool...")
                pool.apply_async(run_task, (event_type, event_kwargs))
                logger.info("Task sent")
