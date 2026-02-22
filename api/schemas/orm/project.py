from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field


class ProjectPhase(str, Enum):
    # Active phases
    DISCOVERY = "discovery"
    DOMAIN_DESIGN = "domain_design"
    BUILD = "build"
    DEPLOY = "deploy"
    HANDOFF = "handoff"
    COMPLETE = "complete"

    # Legacy phases (kept for Beanie deserialization of old documents)
    INTAKE = "intake"
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"


class PhaseHistoryEntry(BaseModel):
    phase: ProjectPhase
    entered_at: datetime
    completed_at: Optional[datetime] = None


class GitHubConfig(BaseModel):
    repo_url: str
    encrypted_pat: str


class Project(Document):
    name: str
    description: Optional[str] = None
    owner_id: Indexed(PydanticObjectId)
    current_phase: ProjectPhase = ProjectPhase.DISCOVERY
    phase_history: list[PhaseHistoryEntry] = []
    github: Optional[GitHubConfig] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "projects"
