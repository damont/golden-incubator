from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from api.schemas.orm.project import ProjectPhase


class ArtifactType(str, Enum):
    PROBLEM_STATEMENT = "problem_statement"
    REQUIREMENTS_DOC = "requirements_doc"
    USER_STORIES = "user_stories"
    ARCHITECTURE_DOC = "architecture_doc"
    DIAGRAM = "diagram"
    SPEC = "spec"


class Artifact(Document):
    project_id: Indexed(PydanticObjectId)
    phase: ProjectPhase
    artifact_type: ArtifactType
    title: str
    content: str  # markdown
    version: int = 1
    created_by: str  # user_id or "agent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "artifacts"
