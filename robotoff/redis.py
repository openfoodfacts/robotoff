from redis import Redis

from robotoff import settings

redis_conn = Redis(host=settings.REDIS_HOST)
