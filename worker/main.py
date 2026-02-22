import asyncio
import logging
import os

from redis.asyncio import Redis

from api.config import get_settings
from api.db import init_db
from api.services.job_service import clear_active_lock
from api.services.agent_service import send_message
from api.services.status_reporter import RedisStatusReporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

STREAM_KEY = "agent_jobs"
GROUP_NAME = "agent-workers"
CONSUMER_NAME = os.environ.get("WORKER_ID", "worker-1")


async def process_job(redis: Redis, job_id: str, project_id: str, user_message: str) -> None:
    """Run the agent loop for a single job."""
    reporter = RedisStatusReporter(redis, job_id)

    # Mark job as processing
    await redis.hset(f"job:{job_id}", "status", "processing")

    try:
        await send_message(project_id, user_message, reporter=reporter)
    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        await reporter.report_error(str(e))
    finally:
        # Always clear the active lock so new jobs can be dispatched
        await clear_active_lock(project_id)


async def run_worker(redis_url: str) -> None:
    """Main worker loop: read jobs from Redis Stream and process them."""
    redis = Redis.from_url(redis_url, decode_responses=True)

    # Ensure consumer group exists
    try:
        await redis.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        logger.info("Created consumer group '%s' on stream '%s'", GROUP_NAME, STREAM_KEY)
    except Exception:
        pass  # Group already exists

    logger.info("Worker '%s' started, listening on stream '%s'", CONSUMER_NAME, STREAM_KEY)

    while True:
        try:
            results = await redis.xreadgroup(
                GROUP_NAME, CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=1,
                block=5000,
            )

            for stream_name, messages in results:
                for message_id, fields in messages:
                    job_id = fields.get("job_id")
                    project_id = fields.get("project_id")
                    user_message = fields.get("user_message")

                    if not all([job_id, project_id, user_message]):
                        logger.warning("Malformed job message %s: %s", message_id, fields)
                        await redis.xack(STREAM_KEY, GROUP_NAME, message_id)
                        continue

                    logger.info("Processing job %s (project %s)", job_id, project_id)

                    await process_job(redis, job_id, project_id, user_message)

                    # ACK after processing (even on failure — failed jobs don't block the queue)
                    await redis.xack(STREAM_KEY, GROUP_NAME, message_id)
                    logger.info("Job %s completed and acknowledged", job_id)

        except asyncio.CancelledError:
            logger.info("Worker shutting down")
            break
        except Exception:
            logger.exception("Worker loop error, retrying in 5s")
            await asyncio.sleep(5)

    await redis.close()


async def main() -> None:
    settings = get_settings()

    # Initialize MongoDB (shared Beanie models)
    await init_db(settings.mongodb_url, settings.mongodb_db_name)

    # Run the worker loop
    await run_worker(settings.redis_url)


if __name__ == "__main__":
    asyncio.run(main())
