import sys

from rq import Connection, Worker

from robotoff import settings
from robotoff.models import with_db
from robotoff.utils import get_logger
from robotoff.workers.queues import queue_names, redis_conn

logger = get_logger()
settings.init_sentry()


@with_db
def load_resources():
    """Load cacheable resources in memory.

    This way, all resources are available in memory before the worker forks.
    """
    logger.info("Loading resources in memory...")

    from robotoff import logos, taxonomy
    from robotoff.prediction.category import matcher
    from robotoff.prediction.object_detection import ObjectDetectionModelRegistry

    matcher.load_resources()
    taxonomy.load_resources()
    logos.load_resources()
    logger.info("Loading object detection model labels...")
    ObjectDetectionModelRegistry.load_all()


def run(burst: bool = False):
    load_resources()
    try:
        with Connection(connection=redis_conn):
            w = Worker(queues=queue_names)
            w.work(logging_level="INFO", burst=burst)
    except ConnectionError as e:
        print(e)
        sys.exit(1)
