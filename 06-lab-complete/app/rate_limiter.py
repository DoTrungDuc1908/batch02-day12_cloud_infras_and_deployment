"""Redis-backed sliding-window rate limiting."""
import time

from fastapi import HTTPException

from app.config import settings
from app.redis_store import redis_client


def check_rate_limit(user_id: str) -> None:
    now = time.time()
    window_seconds = 60
    key = f"rate:{user_id}"

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zcard(key)
    _, current = pipe.execute()

    if current >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": str(window_seconds)},
        )

    redis_client.zadd(key, {str(now): now})
    redis_client.expire(key, window_seconds)
