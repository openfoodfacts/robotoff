import hashlib
import random
import struct
import threading
import time
from typing import Callable, Optional

from rq import Queue
from rq.job import Job

from robotoff import settings
from robotoff.redis import redis_conn
from robotoff.types import ProductIdentifier
from robotoff.utils import get_logger

logger = get_logger(__name__)
high_queues = [
    Queue(f"robotoff-high-{i+1}", connection=redis_conn)
    for i in range(settings.NUM_RQ_WORKERS)
]
low_queue = Queue("robotoff-low", connection=redis_conn)


def get_high_queue(product_id: Optional[ProductIdentifier] = None) -> Queue:
    """Return the high-priority queue that is specific to a product.

    There are as many high priority queues as they are workers.
    We select one of the queues using the product barcode value.
    This way, over all possible barcodes, all queues are returned with equal
    probability, but we make sure we always use the same queue for a single
    product. We greatly reduce the risk of concurrent processing, DB
    deadlocks,...

    If `product_id` is None, we return one of the high-priority queue
    randomly.

    :param product_id: the product identifier
    :return: the selected queue
    """
    if product_id is None:
        return random.choice(high_queues)

    # We compute a md5 hash of the barcode and convert the 4 last bytes to an int (long)
    # This way, we make sure the distribution of `barcode_hash` is uniform and that all
    # queues are sampled evenly with `queue_idx = barcode_hash % len(high_queues)`
    barcode_hash: int = struct.unpack(
        "<l", hashlib.md5(product_id.barcode.encode("utf-8")).digest()[-4:]
    )[0]
    queue_idx = barcode_hash % len(high_queues)
    logger.debug("Selecting queue idx %s for product %s", queue_idx, product_id)
    return high_queues[queue_idx]


def enqueue_in_job(
    func: Callable,
    queue: Queue,
    job_delay: float,
    job_kwargs: Optional[dict] = None,
    **kwargs,
):
    """Enqueue a job in `job_delay` seconds.

    Launch a new Thread where we sleep `job_delay` seconds and the job is
    then enqueued.

    :param job_delay: number of seconds to sleep before sending the job to the
    queue
    """
    threading.Thread(
        target=_enqueue_in_job,
        args=(func, queue, job_delay, job_kwargs, kwargs),
    ).start()


def _enqueue_in_job(
    func: Callable,
    queue: Queue,
    job_delay: float,
    job_kwargs: Optional[dict],
    kwargs,
):
    time.sleep(job_delay)
    enqueue_job(func, queue, job_kwargs, **kwargs)


def enqueue_job(
    func: Callable, queue: Queue, job_kwargs: Optional[dict] = None, **kwargs
):
    """Create a new job from the function and kwargs and enqueue it in the
    queue.

    The function will be called by one of the rq workers. For safety, only
    keyword parameters can be provided to the function.

    :param func: the function to use
    :param queue: the queue to use
    :param job_kwargs: optional kwargs parameters to provide to `Job.create`
    """
    job_kwargs = job_kwargs or {}
    job = Job.create(func=func, kwargs=kwargs, connection=redis_conn, **job_kwargs)
    return queue.enqueue_job(job=job)
