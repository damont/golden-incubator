from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    github_repo_url: Optional[str] = None
    github_pat: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    github_repo_url: Optional[str] = None
    github_pat: Optional[str] = None


class PhaseHistoryResponse(BaseModel):
    phase: str
    entered_at: str
    completed_at: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    current_phase: str
    phase_history: list[PhaseHistoryResponse]
    github_repo_url: Optional[str] = None
    created_at: str
    updated_at: str
