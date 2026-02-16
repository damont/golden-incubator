from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from api.schemas.orm.project import ProjectPhase


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Conversation(Document):
    project_id: Indexed(PydanticObjectId)
    phase: ProjectPhase
    messages: list[Message] = []
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "conversations"
