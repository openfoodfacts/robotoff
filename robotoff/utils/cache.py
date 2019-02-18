import abc
import datetime
from typing import Optional, Callable

from robotoff.utils import get_logger

logger = get_logger(__name__)


class CachedStore(metaclass=abc.ABCMeta):
    def __init__(self,
                 fetch_func: Callable,
                 expiration_timedelta: Optional[datetime.timedelta] = None):
        self.store = None
        self.expires_after: Optional[datetime.datetime] = None
        self.fetch_func: Callable = fetch_func
        self.expiration_timedelta = (expiration_timedelta or
                                     datetime.timedelta(minutes=30))

    def get(self, **kwargs):
        if (self.store is None or
                datetime.datetime.utcnow() >= self.expires_after):
            if self.store is not None:
                logger.info("ProductStore expired, reloading...")

            self.expires_after = (datetime.datetime.utcnow() +
                                  self.expiration_timedelta)
            self.store = self.fetch_func(**kwargs)

        return self.store
