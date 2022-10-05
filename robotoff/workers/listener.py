import threading
import time
from multiprocessing.connection import Listener
from multiprocessing.pool import Pool
from typing import Dict

from sentry_sdk import capture_exception

from robotoff import settings
from robotoff.utils import get_logger
from robotoff.workers.tasks import run_task

settings.init_sentry()

logger = get_logger()


def send_task_to_pool(pool, event_type, event_kwargs, delay):
    """Simply pass the task to a worker in the pool, while eventually applying a delay"""
    if delay:
        time.sleep(delay)
    logger.debug("Sending task to pool...")
    pool.apply_async(run_task, (event_type, event_kwargs))
    logger.debug("Task sent")


def run():
    """This is the event listener, it will receive task requests and launch them"""
    pool: Pool = Pool(settings.WORKER_COUNT, maxtasksperchild=30)

    logger.info("Starting listener server on {}:{}".format(*settings.IPC_ADDRESS))
    logger.info("Starting listener server")

    with Listener(
        settings.IPC_ADDRESS, authkey=settings.IPC_AUTHKEY, family="AF_INET"
    ) as listener:
        while True:
            try:
                logger.debug("Waiting for a connection...")

                with listener.accept() as conn:
                    event = conn.recv()
                    event_type: str = event["type"]
                    logger.info(f"New '{event_type}' event received")
                    event_kwargs: Dict = event.get("meta", {})

                delay = event_kwargs.pop("task_delay", None)
                args = [pool, event_type, event_kwargs, delay]
                if delay:
                    # we have a delay, so spend it in a thread instead of listener main thread
                    threading.Thread(target=send_task_to_pool, args=args).start()
                else:
                    # direct call, it's fast
                    send_task_to_pool(*args)

            except Exception:
                capture_exception()
