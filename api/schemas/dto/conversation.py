from typing import Optional

from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str


class ConversationResponse(BaseModel):
    id: str
    project_id: str
    phase: str
    messages: list[MessageResponse]
    summary: Optional[str]
    created_at: str
    updated_at: str
