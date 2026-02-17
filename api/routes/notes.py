"""
Notes and activity log routes.

Handles project notes, comments, and activity history.
"""

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from beanie import PydanticObjectId

from api.schemas.orm.note import Note, NoteType, ActivityLog
from api.schemas.orm.project import Project, ProjectPhase
from api.utils.auth import get_current_user
from api.schemas.orm.user import User

router = APIRouter(prefix="/api/projects/{project_id}/notes", tags=["notes"])


# ============================================================================
# DTOs
# ============================================================================

class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)
    note_type: NoteType = NoteType.USER_NOTE
    phase: Optional[ProjectPhase] = None
    tags: List[str] = []
    pinned: bool = False
    artifact_id: Optional[str] = None
    entity_ids: List[str] = []


class NoteUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    pinned: Optional[bool] = None


class NoteResponse(BaseModel):
    id: str
    project_id: str
    phase: str
    note_type: str
    content: str
    tags: List[str]
    pinned: bool
    created_by: str
    created_at: str

    class Config:
        from_attributes = True


class ActivityResponse(BaseModel):
    id: str
    project_id: str
    phase: str
    action: str
    actor: str
    target_type: Optional[str]
    target_id: Optional[str]
    details: dict
    created_at: str


# ============================================================================
# Helpers
# ============================================================================

def note_to_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=str(note.id),
        project_id=str(note.project_id),
        phase=note.phase.value,
        note_type=note.note_type.value,
        content=note.content,
        tags=note.tags,
        pinned=note.pinned,
        created_by=note.created_by,
        created_at=note.created_at.isoformat(),
    )


def activity_to_response(log: ActivityLog) -> ActivityResponse:
    return ActivityResponse(
        id=str(log.id),
        project_id=str(log.project_id),
        phase=log.phase.value,
        action=log.action,
        actor=log.actor,
        target_type=log.target_type,
        target_id=str(log.target_id) if log.target_id else None,
        details=log.details,
        created_at=log.created_at.isoformat(),
    )


# ============================================================================
# Note Routes
# ============================================================================

@router.get("", response_model=List[NoteResponse])
async def list_notes(
    project_id: str,
    current_user: User = Depends(get_current_user),
    note_type: Optional[NoteType] = Query(None),
    phase: Optional[ProjectPhase] = Query(None),
    pinned_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List notes for a project."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = {"project_id": project.id}
    if note_type:
        query["note_type"] = note_type
    if phase:
        query["phase"] = phase
    if pinned_only:
        query["pinned"] = True
    
    notes = await Note.find(query).sort("-created_at").skip(offset).limit(limit).to_list()
    return [note_to_response(n) for n in notes]


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(
    project_id: str,
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new note."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    note = Note(
        project_id=project.id,
        phase=data.phase or project.current_phase,
        note_type=data.note_type,
        content=data.content,
        tags=data.tags,
        pinned=data.pinned,
        artifact_id=PydanticObjectId(data.artifact_id) if data.artifact_id else None,
        entity_ids=[PydanticObjectId(e) for e in data.entity_ids],
        created_by=str(current_user.id),
    )
    await note.insert()
    
    # Log activity
    await ActivityLog(
        project_id=project.id,
        phase=project.current_phase,
        action="note_created",
        actor=str(current_user.id),
        target_type="note",
        target_id=note.id,
        details={"note_type": data.note_type.value},
    ).insert()
    
    return note_to_response(note)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    project_id: str,
    note_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a single note."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    note = await Note.get(PydanticObjectId(note_id))
    if not note or note.project_id != project.id:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return note_to_response(note)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    project_id: str,
    note_id: str,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a note."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    note = await Note.get(PydanticObjectId(note_id))
    if not note or note.project_id != project.id:
        raise HTTPException(status_code=404, detail="Note not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(note, key, value)
    
    await note.save()
    return note_to_response(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    project_id: str,
    note_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a note."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    note = await Note.get(PydanticObjectId(note_id))
    if not note or note.project_id != project.id:
        raise HTTPException(status_code=404, detail="Note not found")
    
    await note.delete()


# ============================================================================
# Activity Log Routes
# ============================================================================

@router.get("/activity/log", response_model=List[ActivityResponse])
async def get_activity_log(
    project_id: str,
    current_user: User = Depends(get_current_user),
    phase: Optional[ProjectPhase] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get activity log for a project."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = {"project_id": project.id}
    if phase:
        query["phase"] = phase
    if action:
        query["action"] = action
    
    logs = await ActivityLog.find(query).sort("-created_at").skip(offset).limit(limit).to_list()
    return [activity_to_response(log) for log in logs]
