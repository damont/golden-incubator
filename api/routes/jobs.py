import asyncio
import json
import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from api.config import get_settings
from api.schemas.dto.job import JobDispatchResponse, JobStatusResponse
from api.schemas.orm.project import Project
from api.schemas.orm.user import User
from api.services.job_service import dispatch_job, get_job_status
from api.services.redis import get_redis
from api.utils.auth import get_current_user
from beanie import PydanticObjectId

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project_id}/messages", response_model=JobDispatchResponse)
async def post_message(
    project_id: str,
    data: dict,
    user: User = Depends(get_current_user),
):
    """Dispatch an agent job and return the job_id immediately."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    content = data.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content is required")

    try:
        job_id = await dispatch_job(project_id, content, str(user.id))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return JobDispatchResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}/stream")
async def stream_job(
    request: Request,
    job_id: str,
    token: str = Query(..., description="JWT token for SSE auth"),
):
    """SSE endpoint that streams job status events in real-time."""
    # Authenticate via query parameter (EventSource doesn't support custom headers)
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Verify the job exists
    status = await get_job_status(job_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    redis = get_redis()
    channel = f"job:{job_id}:status"

    async def event_generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        try:
            # Check current state first (handles late-join)
            current = await get_job_status(job_id)
            current_status = current.get("status", "queued")

            # If already complete, send the final state and close
            if current_status == "complete":
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "text": current.get("result", ""),
                        "conversation_id": current.get("conversation_id", ""),
                    }),
                }
                return
            elif current_status == "error":
                yield {
                    "event": "error",
                    "data": json.dumps({"message": current.get("error", "Unknown error")}),
                }
                return

            # Send current status as first event
            if current_status != "queued":
                last_event = current.get("last_event")
                if last_event:
                    try:
                        parsed = json.loads(last_event)
                        event_type = parsed.pop("event", "status")
                        yield {"event": event_type, "data": json.dumps(parsed)}
                    except json.JSONDecodeError:
                        pass

            # Stream real-time events from pub/sub
            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    data = message["data"]
                    try:
                        parsed = json.loads(data)
                        event_type = parsed.pop("event", "status")
                        yield {"event": event_type, "data": json.dumps(parsed)}

                        # Close the stream on terminal events
                        if event_type in ("complete", "error"):
                            return
                    except json.JSONDecodeError:
                        continue
                else:
                    # No message, yield a keepalive comment
                    await asyncio.sleep(0.5)

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return EventSourceResponse(event_generator())


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def poll_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """Poll fallback: get current job status from Redis hash."""
    status = await get_job_status(job_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_id,
        status=status.get("status", "unknown"),
        result=status.get("result"),
        conversation_id=status.get("conversation_id"),
        error=status.get("error"),
    )
