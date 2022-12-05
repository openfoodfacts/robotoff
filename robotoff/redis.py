from typing import Optional

from redis import Redis
from redis_lock import Lock as BaseLock

from robotoff import settings

redis_conn = Redis(host=settings.REDIS_HOST)


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
            self.release()
