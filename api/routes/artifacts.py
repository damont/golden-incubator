import logging
from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException

from api.schemas.dto.artifact import ArtifactCreate, ArtifactResponse
from api.schemas.orm.artifact import Artifact, ArtifactType
from api.schemas.orm.project import Project
from api.schemas.orm.user import User
from api.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def artifact_to_response(artifact: Artifact) -> ArtifactResponse:
    return ArtifactResponse(
        id=str(artifact.id),
        project_id=str(artifact.project_id),
        phase=artifact.phase.value,
        artifact_type=artifact.artifact_type.value,
        title=artifact.title,
        content=artifact.content,
        version=artifact.version,
        created_by=artifact.created_by,
        created_at=artifact.created_at.isoformat(),
        updated_at=artifact.updated_at.isoformat(),
    )


@router.get("/{project_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    project_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    artifacts = await Artifact.find(
        Artifact.project_id == project.id
    ).to_list()
    return [artifact_to_response(a) for a in artifacts]


@router.post("/{project_id}/artifacts", response_model=ArtifactResponse, status_code=201)
async def create_artifact(
    project_id: str,
    data: ArtifactCreate,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = Artifact(
        project_id=project.id,
        phase=project.current_phase,
        artifact_type=ArtifactType(data.artifact_type),
        title=data.title,
        content=data.content,
        created_by=str(user.id),
    )
    await artifact.insert()
    logger.info("Artifact created by user: %s for project %s", data.title, project_id)
    return artifact_to_response(artifact)


@router.get("/{project_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    project_id: str,
    artifact_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await Artifact.get(PydanticObjectId(artifact_id))
    if not artifact or artifact.project_id != project.id:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return artifact_to_response(artifact)


@router.put("/{project_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    project_id: str,
    artifact_id: str,
    data: ArtifactCreate,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await Artifact.get(PydanticObjectId(artifact_id))
    if not artifact or artifact.project_id != project.id:
        raise HTTPException(status_code=404, detail="Artifact not found")

    artifact.title = data.title
    artifact.content = data.content
    artifact.artifact_type = ArtifactType(data.artifact_type)
    artifact.version += 1
    artifact.updated_at = datetime.now(timezone.utc)
    await artifact.save()
    return artifact_to_response(artifact)


@router.delete("/{project_id}/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(
    project_id: str,
    artifact_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await Artifact.get(PydanticObjectId(artifact_id))
    if not artifact or artifact.project_id != project.id:
        raise HTTPException(status_code=404, detail="Artifact not found")

    await artifact.delete()
