from typing import Optional

from pydantic import BaseModel


class ArtifactCreate(BaseModel):
    artifact_type: str
    title: str
    content: str


class ArtifactResponse(BaseModel):
    id: str
    project_id: str
    phase: str
    artifact_type: str
    title: str
    content: str
    version: int
    created_by: str
    created_at: str
    updated_at: str
