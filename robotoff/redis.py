from typing import Optional

from redis import Redis
from redis_lock import Lock as BaseLock
from redis_lock import NotAcquired

from robotoff import settings
from robotoff.utils import get_logger

redis_conn = Redis(host=settings.REDIS_HOST)


logger = get_logger(__name__)


class LockedResourceException(Exception):
    pass


class Lock(BaseLock):
    _enabled = True

    def __init__(
        self,
        name: str,
        blocking: bool = False,
        timeout: Optional[float] = None,
        expire: int = 60,
        **kwargs,
    ):
        self.timeout = timeout
        if timeout is not None:
            blocking = True
        self.blocking = blocking
        if self._enabled:
            super().__init__(redis_conn, name=name, expire=expire, **kwargs)

    def __enter__(self):
        if self._enabled:
            acquired = self.acquire(blocking=self.blocking, timeout=self.timeout)
            if not acquired:
                raise LockedResourceException()
            return self

    def __exit__(self, *args, **kwargs):
        if self._enabled:
            try:
                self.release()
            except NotAcquired:
                logger.warning(
                    "releasing lock failed, lock %s does not exist or expired",
                    self._name,
                )
