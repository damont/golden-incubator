from typing import Optional

from pydantic import BaseModel


class ArtifactCreate(BaseModel):
    artifact_type: str
    title: str
    content: str
    step_order: Optional[int] = None


class ArtifactResponse(BaseModel):
    id: str
    project_id: str
    phase: str
    artifact_type: str
    title: str
    content: str
    step_order: int
    version: int
    created_by: str
    created_at: str
    updated_at: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
