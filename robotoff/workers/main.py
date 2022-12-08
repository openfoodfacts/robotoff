import sys

from rq import Connection, Worker

from robotoff import settings
from robotoff.models import with_db
from robotoff.utils import get_logger
from robotoff.workers.queues import redis_conn

logger = get_logger()
settings.init_sentry()


@with_db
def load_resources(refresh: bool = False):
    """Load cacheable resources in memory.

    This way, all resources are available in memory before the worker forks.
    """
    if refresh:
        logger.info("Refreshing worker resource caches...")
    else:
        logger.info("Loading resources in memory...")

    from robotoff import logos, taxonomy
    from robotoff.prediction.category import matcher
    from robotoff.prediction.object_detection import ObjectDetectionModelRegistry

    matcher.load_resources()
    taxonomy.load_resources()
    logos.load_resources()

    if not refresh:
        logger.info("Loading object detection model labels...")
        ObjectDetectionModelRegistry.load_all()


class CustomWorker(Worker):
    def run_maintenance_tasks(self):
        super().run_maintenance_tasks()
        load_resources(refresh=True)


def run(queues: list[str], burst: bool = False):
    load_resources()
    try:
        with Connection(connection=redis_conn):
            w = CustomWorker(queues=queues)
            w.work(logging_level="INFO", burst=burst)
    except ConnectionError as e:
        print(e)
        sys.exit(1)
