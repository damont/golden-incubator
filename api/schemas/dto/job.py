from pydantic import BaseModel


class JobDispatchResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: str | None = None
    conversation_id: str | None = None
    error: str | None = None
