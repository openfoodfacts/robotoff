import datetime
from typing import Callable, Optional

from robotoff.utils import get_logger

logger = get_logger(__name__)


class CachedStore:
    def __init__(self, fetch_func: Callable, expiration_interval: Optional[int] = 30):
        self.store = None
        self.expires_after: Optional[datetime.datetime] = None
        self.fetch_func: Callable = fetch_func
        self.expiration_timedelta: Optional[datetime.timedelta]

        if expiration_interval is not None:
            self.expiration_timedelta = datetime.timedelta(minutes=expiration_interval)
        else:
            self.expiration_timedelta = None

    def get(self, **kwargs):
        if self.store is None or (
            self.expiration_timedelta is not None
            and datetime.datetime.utcnow() >= self.expires_after
        ):
            if self.store is not None:
                logger.info("CachedStore expired, reloading...")

            if self.expiration_timedelta is not None:
                self.expires_after = (
                    datetime.datetime.utcnow() + self.expiration_timedelta
                )
            self.store = self.fetch_func(**kwargs)

        return self.store
