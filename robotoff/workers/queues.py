import threading
import time
from typing import Callable, Optional

from rq import Queue
from rq.job import Job

from robotoff.redis import redis_conn
from robotoff.types import WorkerQueue

high_queue = Queue(WorkerQueue.robotoff_high.value, connection=redis_conn)
low_queue = Queue(WorkerQueue.robotoff_low.value, connection=redis_conn)


def enqueue_in_job(
    func: Callable,
    queue: Queue,
    job_delay: float,
    job_kwargs: Optional[dict] = None,
    **kwargs
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
