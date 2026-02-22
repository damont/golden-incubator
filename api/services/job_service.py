import json
import logging
import uuid

from redis.asyncio import Redis

from api.services.redis import get_redis

logger = logging.getLogger(__name__)

STREAM_KEY = "agent_jobs"


async def dispatch_job(
    project_id: str, user_message: str, user_id: str
) -> str:
    """Dispatch an agent job to the Redis stream. Returns the job_id."""
    redis = get_redis()

    # Dedup: prevent concurrent agent runs on the same project
    lock_key = f"job:active:{project_id}"
    existing = await redis.get(lock_key)
    if existing:
        raise ValueError(f"An agent job is already running for this project (job {existing})")

    job_id = str(uuid.uuid4())

    # Set active lock (expires in 5 minutes as safety net)
    await redis.set(lock_key, job_id, ex=300)

    # Create job hash with initial state
    hash_key = f"job:{job_id}"
    await redis.hset(hash_key, mapping={
        "status": "queued",
        "project_id": project_id,
        "user_id": user_id,
        "user_message": user_message,
    })
    await redis.expire(hash_key, 3600)

    # Add to the job stream
    await redis.xadd(STREAM_KEY, {
        "job_id": job_id,
        "project_id": project_id,
        "user_id": user_id,
        "user_message": user_message,
    })

    logger.info("Dispatched job %s for project %s", job_id, project_id)
    return job_id


async def get_job_status(job_id: str) -> dict:
    """Read current job state from the Redis hash."""
    redis = get_redis()
    hash_key = f"job:{job_id}"
    data = await redis.hgetall(hash_key)
    if not data:
        return {"job_id": job_id, "status": "not_found"}
    return {"job_id": job_id, **data}


async def clear_active_lock(project_id: str, redis: "Redis | None" = None) -> None:
    """Remove the active job lock for a project."""
    if redis is None:
        redis = get_redis()
    await redis.delete(f"job:active:{project_id}")
