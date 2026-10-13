"""Redis connection and client management for Sherlog queue and streams."""

import logging
from typing import Optional
import redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Reusable client cache for connection reuse
_redis_pool: Optional[redis.ConnectionPool] = None


def get_redis_pool(redis_url: Optional[str] = None) -> redis.ConnectionPool:
    """Return or create shared Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        url = redis_url or settings.REDIS_URL
        _redis_pool = redis.ConnectionPool.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=5.0,
            health_check_interval=30,
        )
    return _redis_pool


def get_redis_client(redis_url: Optional[str] = None) -> redis.Redis:
    """Return a managed Redis client using connection pool.

    decode_responses=True ensures string messages rather than raw bytes.
    """
    if redis_url:
        # Separate pool/client if custom URL is specified
        return redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=5.0,
        )
    pool = get_redis_pool()
    return redis.Redis(connection_pool=pool)


def is_redis_available(client: Optional[redis.Redis] = None) -> bool:
    """Perform quick non-blocking check if Redis is responsive."""
    try:
        r = client or get_redis_client()
        return bool(r.ping())
    except (ConnectionError, TimeoutError, RedisError, Exception) as exc:
        logger.debug("Redis ping check failed: %s", exc)
        return False
