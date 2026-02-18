"""
Project progress and phase management routes.

Provides visual progress data for the UI sidebar.
"""

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from beanie import PydanticObjectId

from api.schemas.orm.project import Project, ProjectPhase, PhaseHistoryEntry
from api.schemas.orm.entity import Entity, EntityType, EntityStatus
from api.schemas.orm.note import Note, NoteType, ActivityLog
from api.schemas.orm.artifact import Artifact
from api.utils.auth import get_current_user
from api.schemas.orm.user import User

router = APIRouter(prefix="/api/projects/{project_id}/progress", tags=["progress"])


# ============================================================================
# DTOs
# ============================================================================

class PhaseInfo(BaseModel):
    """Information about a single phase."""
    phase: str
    name: str
    description: str
    status: str  # "completed", "current", "upcoming"
    entered_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Stats for this phase
    requirements_count: int = 0
    instructions_count: int = 0
    instructions_completed: int = 0
    notes_count: int = 0
    artifacts_count: int = 0


class ProgressResponse(BaseModel):
    """Full progress overview for sidebar display."""
    project_id: str
    project_name: str
    current_phase: str
    current_phase_index: int
    total_phases: int
    percent_complete: int  # 0-100
    
    phases: List[PhaseInfo]
    
    # Pending items across all phases
    pending_instructions: int
    open_questions: int
    total_requirements: int
    confirmed_requirements: int


class PhaseAdvanceRequest(BaseModel):
    """Request to advance to next phase."""
    force: bool = False  # Skip validation checks


class PhaseAdvanceResponse(BaseModel):
    """Response after phase advance."""
    success: bool
    previous_phase: str
    new_phase: str
    message: str
    warnings: List[str] = []


# ============================================================================
# Phase Metadata
# ============================================================================

# Map legacy phases that were removed from the flow to their replacement
_LEGACY_PHASE_MAP = {
    ProjectPhase.REQUIREMENTS: ProjectPhase.INTAKE,
}


def _effective_phase(phase: ProjectPhase) -> ProjectPhase:
    """Resolve legacy phases to their current equivalent."""
    return _LEGACY_PHASE_MAP.get(phase, phase)


PHASE_ORDER = [
    ProjectPhase.INTAKE,
    ProjectPhase.ARCHITECTURE,
    ProjectPhase.BUILD,
    ProjectPhase.DEPLOY,
    ProjectPhase.HANDOFF,
    ProjectPhase.COMPLETE,
]

PHASE_INFO = {
    ProjectPhase.INTAKE: {
        "name": "Intake",
        "description": "Discovery, requirements gathering, and problem definition",
    },
    ProjectPhase.ARCHITECTURE: {
        "name": "Architecture",
        "description": "System design and technical planning",
    },
    ProjectPhase.BUILD: {
        "name": "Build",
        "description": "Development and implementation",
    },
    ProjectPhase.DEPLOY: {
        "name": "Deploy",
        "description": "Testing, staging, and production deployment",
    },
    ProjectPhase.HANDOFF: {
        "name": "Handoff",
        "description": "Documentation and client training",
    },
    ProjectPhase.COMPLETE: {
        "name": "Complete",
        "description": "Project delivered and closed",
    },
}


# ============================================================================
# Routes
# ============================================================================

@router.get("", response_model=ProgressResponse)
async def get_progress(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive progress overview for sidebar display.
    
    Returns phase status, completion stats, and pending items.
    """
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Build phase history lookup
    phase_history = {h.phase: h for h in project.phase_history}
    current_idx = PHASE_ORDER.index(_effective_phase(project.current_phase))
    
    # Get counts for each phase
    phases = []
    total_pending_instructions = 0
    total_open_questions = 0
    total_requirements = 0
    confirmed_requirements = 0
    
    for i, phase in enumerate(PHASE_ORDER):
        # Determine status
        if i < current_idx:
            status = "completed"
        elif i == current_idx:
            status = "current"
        else:
            status = "upcoming"
        
        # Get history entry
        history = phase_history.get(phase)
        
        # Count entities for this phase
        req_count = await Entity.find({
            "project_id": project.id,
            "phase": phase,
            "entity_type": EntityType.REQUIREMENT,
        }).count()
        
        instr_count = await Entity.find({
            "project_id": project.id,
            "phase": phase,
            "entity_type": EntityType.INSTRUCTION,
        }).count()
        
        instr_completed = await Entity.find({
            "project_id": project.id,
            "phase": phase,
            "entity_type": EntityType.INSTRUCTION,
            "status": EntityStatus.COMPLETED,
        }).count()
        
        questions = await Entity.find({
            "project_id": project.id,
            "phase": phase,
            "entity_type": EntityType.QUESTION,
            "status": {"$nin": [EntityStatus.COMPLETED, EntityStatus.REJECTED]},
        }).count()
        
        notes = await Note.find({
            "project_id": project.id,
            "phase": phase,
        }).count()
        
        artifacts = await Artifact.find({
            "project_id": project.id,
            "phase": phase,
        }).count()
        
        # Track confirmed requirements
        confirmed_in_phase = await Entity.find({
            "project_id": project.id,
            "phase": phase,
            "entity_type": EntityType.REQUIREMENT,
            "status": EntityStatus.CONFIRMED,
        }).count()
        
        total_requirements += req_count
        confirmed_requirements += confirmed_in_phase
        total_pending_instructions += (instr_count - instr_completed)
        total_open_questions += questions
        
        info = PHASE_INFO[phase]
        phases.append(PhaseInfo(
            phase=phase.value,
            name=info["name"],
            description=info["description"],
            status=status,
            entered_at=history.entered_at.isoformat() if history else None,
            completed_at=history.completed_at.isoformat() if history and history.completed_at else None,
            requirements_count=req_count,
            instructions_count=instr_count,
            instructions_completed=instr_completed,
            notes_count=notes,
            artifacts_count=artifacts,
        ))
    
    # Calculate percent complete (simple: based on phase index)
    # Could be made more sophisticated based on phase deliverables
    if project.current_phase == ProjectPhase.COMPLETE:
        percent_complete = 100
    else:
        percent_complete = int((current_idx / (len(PHASE_ORDER) - 1)) * 100)
    
    return ProgressResponse(
        project_id=str(project.id),
        project_name=project.name,
        current_phase=project.current_phase.value,
        current_phase_index=current_idx,
        total_phases=len(PHASE_ORDER),
        percent_complete=percent_complete,
        phases=phases,
        pending_instructions=total_pending_instructions,
        open_questions=total_open_questions,
        total_requirements=total_requirements,
        confirmed_requirements=confirmed_requirements,
    )


@router.post("/advance", response_model=PhaseAdvanceResponse)
async def advance_phase(
    project_id: str,
    data: PhaseAdvanceRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Advance project to the next phase.
    
    Validates that current phase requirements are met unless force=True.
    """
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    effective = _effective_phase(project.current_phase)
    current_idx = PHASE_ORDER.index(effective)

    if current_idx >= len(PHASE_ORDER) - 1:
        raise HTTPException(status_code=400, detail="Project is already complete")

    next_phase = PHASE_ORDER[current_idx + 1]
    warnings = []
    
    # Validation checks (skip if force=True)
    if not data.force:
        # Check for incomplete instructions
        pending_instructions = await Entity.find({
            "project_id": project.id,
            "phase": project.current_phase,
            "entity_type": EntityType.INSTRUCTION,
            "status": {"$nin": [EntityStatus.COMPLETED, EntityStatus.REJECTED]},
        }).count()
        
        if pending_instructions > 0:
            warnings.append(f"{pending_instructions} instructions not completed")
        
        # Check for open questions
        open_questions = await Entity.find({
            "project_id": project.id,
            "phase": project.current_phase,
            "entity_type": EntityType.QUESTION,
            "status": {"$nin": [EntityStatus.COMPLETED, EntityStatus.REJECTED]},
        }).count()
        
        if open_questions > 0:
            warnings.append(f"{open_questions} questions still open")
        
        # Check for unconfirmed requirements (in intake phase)
        if project.current_phase == ProjectPhase.INTAKE:
            unconfirmed = await Entity.find({
                "project_id": project.id,
                "phase": project.current_phase,
                "entity_type": EntityType.REQUIREMENT,
                "status": EntityStatus.DRAFT,
            }).count()

            if unconfirmed > 0:
                warnings.append(f"{unconfirmed} requirements not confirmed")
        
        # If warnings and not forcing, block advancement
        if warnings:
            return PhaseAdvanceResponse(
                success=False,
                previous_phase=project.current_phase.value,
                new_phase=project.current_phase.value,
                message="Phase has incomplete items. Set force=True to advance anyway.",
                warnings=warnings,
            )
    
    # Update phase history
    now = datetime.now(timezone.utc)
    
    # Mark current phase as completed
    for entry in project.phase_history:
        if entry.phase == project.current_phase and entry.completed_at is None:
            entry.completed_at = now
            break
    
    # Add new phase entry
    project.phase_history.append(PhaseHistoryEntry(
        phase=next_phase,
        entered_at=now,
    ))
    
    previous_phase = project.current_phase
    project.current_phase = next_phase
    project.updated_at = now
    await project.save()
    
    # Log activity
    await ActivityLog(
        project_id=project.id,
        phase=next_phase,
        action="phase_advanced",
        actor=str(current_user.id),
        details={
            "from_phase": previous_phase.value,
            "to_phase": next_phase.value,
            "forced": data.force,
        },
    ).insert()
    
    # Create system note
    await Note(
        project_id=project.id,
        phase=next_phase,
        note_type=NoteType.PHASE_CHANGE,
        content=f"Advanced from **{PHASE_INFO[previous_phase]['name']}** to **{PHASE_INFO[next_phase]['name']}**",
        from_phase=previous_phase,
        to_phase=next_phase,
        created_by="system",
    ).insert()
    
    return PhaseAdvanceResponse(
        success=True,
        previous_phase=previous_phase.value,
        new_phase=next_phase.value,
        message=f"Advanced to {PHASE_INFO[next_phase]['name']} phase",
        warnings=warnings,
    )
