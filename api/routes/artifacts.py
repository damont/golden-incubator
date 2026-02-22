import logging
from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response

from api.schemas.dto.artifact import ArtifactCreate, ArtifactResponse
from api.schemas.orm.artifact import Artifact, ArtifactType
from api.schemas.orm.project import Project, ProjectPhase
from api.schemas.orm.user import User
from api.services.storage import get_storage
from api.utils.auth import get_current_user

# Legacy phases that were consolidated into current phases
_LEGACY_PHASE_MAP = {
    ProjectPhase.INTAKE: ProjectPhase.DISCOVERY,
    ProjectPhase.REQUIREMENTS: ProjectPhase.DISCOVERY,
    ProjectPhase.ARCHITECTURE: ProjectPhase.DOMAIN_DESIGN,
}


def _phase_aliases(phase: ProjectPhase) -> list[str]:
    """Return all phase values (current + legacy) that map to this phase."""
    aliases = [phase.value]
    for legacy, target in _LEGACY_PHASE_MAP.items():
        if target == phase:
            aliases.append(legacy.value)
    return aliases

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


async def _next_step_order(project_id: PydanticObjectId, phase: ProjectPhase) -> int:
    """Get the next step_order for a new artifact in a project+phase."""
    phase_values = _phase_aliases(phase)
    last = await Artifact.find(
        {"project_id": project_id, "phase": {"$in": phase_values}}
    ).sort("-step_order").limit(1).to_list()
    return (last[0].step_order + 1) if last else 1


def artifact_to_response(artifact: Artifact) -> ArtifactResponse:
    return ArtifactResponse(
        id=str(artifact.id),
        project_id=str(artifact.project_id),
        phase=artifact.phase.value,
        artifact_type=artifact.artifact_type.value,
        title=artifact.title,
        content=artifact.content,
        step_order=artifact.step_order,
        version=artifact.version,
        created_by=artifact.created_by,
        created_at=artifact.created_at.isoformat(),
        updated_at=artifact.updated_at.isoformat(),
        file_name=artifact.file_name,
        file_size=artifact.file_size,
        content_type=artifact.content_type,
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
    ).sort("phase", "step_order").to_list()
    return [artifact_to_response(a) for a in artifacts]


@router.post("/{project_id}/artifacts/upload", response_model=ArtifactResponse, status_code=201)
async def upload_artifact(
    project_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (10 MB limit)")

    step_order = await _next_step_order(project.id, project.current_phase)
    artifact = Artifact(
        project_id=project.id,
        phase=project.current_phase,
        artifact_type=ArtifactType.UPLOAD,
        title=file.filename or "Uploaded file",
        content="",
        step_order=step_order,
        file_name=file.filename,
        file_size=len(data),
        content_type=file.content_type or "application/octet-stream",
        created_by=str(user.id),
    )
    await artifact.insert()

    storage_key = f"{project_id}/{artifact.id}_{file.filename}"
    artifact.storage_key = storage_key
    await artifact.save()

    storage = get_storage()
    await storage.save(storage_key, data, artifact.content_type or "application/octet-stream")

    logger.info("File uploaded: %s for project %s", file.filename, project_id)
    return artifact_to_response(artifact)


@router.get("/{project_id}/artifacts/{artifact_id}/download")
async def download_artifact(
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

    if not artifact.storage_key:
        raise HTTPException(status_code=404, detail="No file associated with this artifact")

    storage = get_storage()
    try:
        data = await storage.load(artifact.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on storage")

    return Response(
        content=data,
        media_type=artifact.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.file_name or "download"}"'
        },
    )


@router.post("/{project_id}/artifacts", response_model=ArtifactResponse, status_code=201)
async def create_artifact(
    project_id: str,
    data: ArtifactCreate,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    step_order = data.step_order if data.step_order is not None else await _next_step_order(project.id, project.current_phase)
    artifact = Artifact(
        project_id=project.id,
        phase=project.current_phase,
        artifact_type=ArtifactType(data.artifact_type),
        title=data.title,
        content=data.content,
        step_order=step_order,
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

    if artifact.storage_key:
        storage = get_storage()
        await storage.delete(artifact.storage_key)

    await artifact.delete()
