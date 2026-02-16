import logging
from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException

from api.schemas.dto.project import (
    PhaseHistoryResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from api.schemas.orm.project import GitHubConfig, PhaseHistoryEntry, Project
from api.schemas.orm.user import User
from api.services.encryption import encrypt_pat
from api.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        current_phase=project.current_phase.value,
        phase_history=[
            PhaseHistoryResponse(
                phase=ph.phase.value,
                entered_at=ph.entered_at.isoformat(),
                completed_at=ph.completed_at.isoformat() if ph.completed_at else None,
            )
            for ph in project.phase_history
        ],
        github_repo_url=project.github.repo_url if project.github else None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(user: User = Depends(get_current_user)):
    projects = await Project.find(
        Project.owner_id == user.id
    ).to_list()
    return [project_to_response(p) for p in projects]


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    github = None
    if data.github_repo_url and data.github_pat:
        github = GitHubConfig(
            repo_url=data.github_repo_url,
            encrypted_pat=encrypt_pat(data.github_pat),
        )

    project = Project(
        name=data.name,
        description=data.description,
        owner_id=user.id,
        phase_history=[
            PhaseHistoryEntry(phase="intake", entered_at=now)
        ],
        github=github,
        created_at=now,
        updated_at=now,
    )
    await project.insert()
    logger.info("Project created: %s by user %s", project.name, user.id)
    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: User = Depends(get_current_user)):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, data: ProjectUpdate, user: User = Depends(get_current_user)
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.github_repo_url is not None and data.github_pat is not None:
        project.github = GitHubConfig(
            repo_url=data.github_repo_url,
            encrypted_pat=encrypt_pat(data.github_pat),
        )
    elif data.github_repo_url is not None and project.github:
        project.github.repo_url = data.github_repo_url

    project.updated_at = datetime.now(timezone.utc)
    await project.save()
    return project_to_response(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, user: User = Depends(get_current_user)):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    await project.delete()
    logger.info("Project deleted: %s by user %s", project_id, user.id)
