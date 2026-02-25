import json
import logging
from typing import Protocol

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class StatusReporter(Protocol):
    async def report_thinking(self, iteration: int) -> None: ...
    async def report_generating(self, detail: str) -> None: ...
    async def report_tool_call(self, tool_name: str, tool_input: dict) -> None: ...
    async def report_tool_result(self, tool_name: str, result: str) -> None: ...
    async def report_complete(self, text: str, conversation_id: str) -> None: ...
    async def report_error(self, message: str) -> None: ...


class NullStatusReporter:
    """No-op reporter for tests and direct calls."""

    async def report_thinking(self, iteration: int) -> None:
        pass

    async def report_generating(self, detail: str) -> None:
        pass

    async def report_tool_call(self, tool_name: str, tool_input: dict) -> None:
        pass

    async def report_tool_result(self, tool_name: str, result: str) -> None:
        pass

    async def report_complete(self, text: str, conversation_id: str) -> None:
        pass

    async def report_error(self, message: str) -> None:
        pass


class RedisStatusReporter:
    """Publishes status events to Redis Pub/Sub and updates a Redis Hash."""

    def __init__(self, redis: Redis, job_id: str):
        self._redis = redis
        self._job_id = job_id
        self._channel = f"job:{job_id}:status"
        self._hash_key = f"job:{job_id}"

    async def _publish(self, event: str, data: dict) -> None:
        payload = json.dumps({"event": event, **data})
        await self._redis.publish(self._channel, payload)
        await self._redis.hset(self._hash_key, "status", event)
        await self._redis.hset(self._hash_key, "last_event", payload)

    async def report_thinking(self, iteration: int) -> None:
        await self._publish("thinking", {"iteration": iteration})

    async def report_generating(self, detail: str) -> None:
        await self._publish("generating", {"detail": detail})

    async def report_tool_call(self, tool_name: str, tool_input: dict) -> None:
        # Summarize input to avoid publishing large payloads
        summary = ", ".join(f"{k}: {str(v)[:80]}" for k, v in tool_input.items()
                           if k != "content")
        await self._publish("tool_call", {
            "tool": tool_name,
            "input_summary": summary,
        })

    async def report_tool_result(self, tool_name: str, result: str) -> None:
        # Parse result to get a useful summary
        try:
            parsed = json.loads(result)
            summary = ", ".join(f"{k}: {v}" for k, v in parsed.items())
        except (json.JSONDecodeError, AttributeError):
            summary = result[:200]
        await self._publish("tool_result", {
            "tool": tool_name,
            "summary": summary,
        })

    async def report_complete(self, text: str, conversation_id: str) -> None:
        await self._publish("complete", {
            "text": text,
            "conversation_id": conversation_id,
        })
        await self._redis.hset(self._hash_key, "result", text)
        await self._redis.hset(self._hash_key, "conversation_id", conversation_id)
        # Expire the hash after 1 hour
        await self._redis.expire(self._hash_key, 3600)

    async def report_error(self, message: str) -> None:
        await self._publish("error", {"message": message})
        await self._redis.hset(self._hash_key, "error", message)
        await self._redis.expire(self._hash_key, 3600)
