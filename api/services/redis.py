import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def init_redis(url: str) -> Redis:
    """Initialize the Redis connection. Call during app lifespan startup."""
    global _redis
    _redis = Redis.from_url(url, decode_responses=True)
    await _redis.ping()
    logger.info("Connected to Redis")
    return _redis


async def close_redis():
    """Close the Redis connection. Call during app lifespan shutdown."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
        logger.info("Disconnected from Redis")


def get_redis() -> Redis:
    """Get the current Redis connection. Raises if not initialized."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis
