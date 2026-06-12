"""Redis connection shared by app modules."""
import redis

from app.config import settings


redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
    retry_on_timeout=False,
)


def ping_redis() -> bool:
    return redis_client.ping() is True
