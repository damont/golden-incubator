"""
Step management routes.

Handles CRUD operations for low-level steps within phases.
"""

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from beanie import PydanticObjectId

from api.schemas.orm.step import Step, StepStatus, DEFAULT_PHASE_STEPS
from api.schemas.orm.project import Project, ProjectPhase
from api.utils.auth import get_current_user
from api.schemas.orm.user import User

router = APIRouter(prefix="/api/projects/{project_id}/steps", tags=["steps"])


# ============================================================================
# DTOs
# ============================================================================

class StepCreate(BaseModel):
    phase: ProjectPhase
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    order: int = 0


class StepUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[StepStatus] = None
    output_content: Optional[str] = None
    order: Optional[int] = None


class StepResponse(BaseModel):
    id: str
    project_id: str
    phase: str
    name: str
    slug: str
    description: Optional[str]
    order: int
    status: str
    output_file: Optional[str]
    output_content: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str


# ============================================================================
# Helpers
# ============================================================================

def step_to_response(step: Step) -> StepResponse:
    return StepResponse(
        id=str(step.id),
        project_id=str(step.project_id),
        phase=step.phase.value,
        name=step.name,
        slug=step.slug,
        description=step.description,
        order=step.order,
        status=step.status.value,
        output_file=step.output_file,
        output_content=step.output_content,
        started_at=step.started_at.isoformat() if step.started_at else None,
        completed_at=step.completed_at.isoformat() if step.completed_at else None,
        created_at=step.created_at.isoformat(),
        updated_at=step.updated_at.isoformat(),
    )


# ============================================================================
# Routes
# ============================================================================

@router.get("", response_model=List[StepResponse])
async def list_steps(
    project_id: str,
    current_user: User = Depends(get_current_user),
    phase: Optional[ProjectPhase] = Query(None),
):
    """List steps for a project, optionally filtered by phase."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = {"project_id": project.id}
    if phase:
        query["phase"] = phase
    
    steps = await Step.find(query).sort("+phase", "+order").to_list()
    return [step_to_response(s) for s in steps]


@router.post("/initialize", response_model=List[StepResponse])
async def initialize_steps(
    project_id: str,
    current_user: User = Depends(get_current_user),
    phase: Optional[ProjectPhase] = Query(None, description="Initialize specific phase only"),
):
    """
    Initialize default steps for a project.
    
    If phase is specified, only initializes that phase.
    Otherwise, initializes all phases.
    """
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    phases_to_init = [phase] if phase else list(DEFAULT_PHASE_STEPS.keys())
    created_steps = []
    
    for p in phases_to_init:
        if p not in DEFAULT_PHASE_STEPS:
            continue
        
        # Check if steps already exist for this phase
        existing = await Step.find(
            Step.project_id == project.id,
            Step.phase == p,
        ).count()
        
        if existing > 0:
            continue  # Don't reinitialize
        
        for i, step_def in enumerate(DEFAULT_PHASE_STEPS[p]):
            step = Step(
                project_id=project.id,
                phase=p,
                name=step_def["name"],
                slug=step_def["slug"],
                description=step_def.get("description"),
                order=i,
                output_file=f"{p.value}/{step_def['slug']}.md",
            )
            await step.insert()
            created_steps.append(step)
    
    return [step_to_response(s) for s in created_steps]


@router.post("", response_model=StepResponse, status_code=201)
async def create_step(
    project_id: str,
    data: StepCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a custom step."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    step = Step(
        project_id=project.id,
        phase=data.phase,
        name=data.name,
        slug=data.slug,
        description=data.description,
        order=data.order,
        output_file=f"{data.phase.value}/{data.slug}.md",
    )
    await step.insert()
    
    return step_to_response(step)


@router.get("/{step_id}", response_model=StepResponse)
async def get_step(
    project_id: str,
    step_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a single step."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    step = await Step.get(PydanticObjectId(step_id))
    if not step or step.project_id != project.id:
        raise HTTPException(status_code=404, detail="Step not found")
    
    return step_to_response(step)


@router.patch("/{step_id}", response_model=StepResponse)
async def update_step(
    project_id: str,
    step_id: str,
    data: StepUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a step."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    step = await Step.get(PydanticObjectId(step_id))
    if not step or step.project_id != project.id:
        raise HTTPException(status_code=404, detail="Step not found")
    
    update_data = data.model_dump(exclude_unset=True)
    now = datetime.now(timezone.utc)
    
    # Handle status transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == StepStatus.IN_PROGRESS and step.status == StepStatus.NOT_STARTED:
            step.started_at = now
        elif new_status == StepStatus.COMPLETED:
            step.completed_at = now
    
    for key, value in update_data.items():
        setattr(step, key, value)
    
    step.updated_at = now
    await step.save()
    
    return step_to_response(step)


@router.delete("/{step_id}", status_code=204)
async def delete_step(
    project_id: str,
    step_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a step."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    step = await Step.get(PydanticObjectId(step_id))
    if not step or step.project_id != project.id:
        raise HTTPException(status_code=404, detail="Step not found")
    
    await step.delete()
