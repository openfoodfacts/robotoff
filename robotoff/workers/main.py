import sys

from rq import Connection, Worker

from robotoff import settings
from robotoff.utils import get_logger
from robotoff.workers.queues import queue_names, redis_conn

logger = get_logger()
settings.init_sentry()


def load_resources():
    """Load cacheable resources in memory.

    This way, all resources are available in memory before the worker forks.
    """
    logger.info("Loading resources in workers...")

    from robotoff import taxonomy
    from robotoff.prediction.category import matcher

    matcher.load_resources()
    taxonomy.load_resources()


def run(burst: bool = False):
    load_resources()
    try:
        with Connection(connection=redis_conn):
            w = Worker(queues=queue_names)
            w.work(logging_level="INFO", burst=burst)
    except ConnectionError as e:
        print(e)
        sys.exit(1)
