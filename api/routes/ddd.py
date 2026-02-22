"""
Domain-Driven Design routes.

Handles DDD artifacts: entities, subdomains, and events.
Includes scaffold generation from intake content.
"""

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from beanie import PydanticObjectId

from api.schemas.orm.ddd import (
    DomainEntity,
    Subdomain,
    DomainEvent,
    SubdomainType,
)
from api.schemas.orm.project import Project, ProjectPhase
from api.routes.progress import _effective_phase
from api.utils.auth import get_current_user
from api.schemas.orm.user import User
from api.services.ddd_generator import ddd_generator

router = APIRouter(prefix="/api/projects/{project_id}/ddd", tags=["ddd"])


# ============================================================================
# DTOs
# ============================================================================

class DomainEntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str
    subdomain_id: Optional[str] = None
    properties: List[dict] = []
    relationships: List[dict] = []
    is_aggregate_root: bool = False


class DomainEntityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    subdomain_id: Optional[str] = None
    properties: Optional[List[dict]] = None
    relationships: Optional[List[dict]] = None
    is_aggregate_root: Optional[bool] = None
    is_confirmed: Optional[bool] = None


class DomainEntityResponse(BaseModel):
    id: str
    project_id: str
    subdomain_id: Optional[str]
    name: str
    description: str
    properties: List[dict]
    relationships: List[dict]
    is_aggregate_root: bool
    is_confirmed: bool
    source_text: Optional[str]
    created_at: str
    updated_at: str


class SubdomainCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str
    subdomain_type: SubdomainType = SubdomainType.SUPPORTING
    responsibilities: List[str] = []


class SubdomainUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    subdomain_type: Optional[SubdomainType] = None
    responsibilities: Optional[List[str]] = None
    is_confirmed: Optional[bool] = None


class SubdomainResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    subdomain_type: str
    responsibilities: List[str]
    is_confirmed: bool
    entity_count: int = 0
    event_count: int = 0
    created_at: str
    updated_at: str


class DomainEventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str
    subdomain_id: Optional[str] = None
    payload: List[dict] = []
    triggered_by: Optional[str] = None
    subscribers: List[str] = []


class DomainEventUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    subdomain_id: Optional[str] = None
    payload: Optional[List[dict]] = None
    triggered_by: Optional[str] = None
    subscribers: Optional[List[str]] = None
    is_confirmed: Optional[bool] = None


class DomainEventResponse(BaseModel):
    id: str
    project_id: str
    subdomain_id: Optional[str]
    name: str
    description: str
    payload: List[dict]
    triggered_by: Optional[str]
    subscribers: List[str]
    is_confirmed: bool
    created_at: str
    updated_at: str


class DDDScaffoldResponse(BaseModel):
    entities: List[DomainEntityResponse]
    subdomains: List[SubdomainResponse]
    events: List[DomainEventResponse]
    message: str


# ============================================================================
# Helpers
# ============================================================================

async def entity_to_response(entity: DomainEntity) -> DomainEntityResponse:
    return DomainEntityResponse(
        id=str(entity.id),
        project_id=str(entity.project_id),
        subdomain_id=str(entity.subdomain_id) if entity.subdomain_id else None,
        name=entity.name,
        description=entity.description,
        properties=entity.properties,
        relationships=entity.relationships,
        is_aggregate_root=entity.is_aggregate_root,
        is_confirmed=entity.is_confirmed,
        source_text=entity.source_text,
        created_at=entity.created_at.isoformat(),
        updated_at=entity.updated_at.isoformat(),
    )


async def subdomain_to_response(subdomain: Subdomain) -> SubdomainResponse:
    # Count related entities and events
    entity_count = await DomainEntity.find(DomainEntity.subdomain_id == subdomain.id).count()
    event_count = await DomainEvent.find(DomainEvent.subdomain_id == subdomain.id).count()
    
    return SubdomainResponse(
        id=str(subdomain.id),
        project_id=str(subdomain.project_id),
        name=subdomain.name,
        description=subdomain.description,
        subdomain_type=subdomain.subdomain_type.value,
        responsibilities=subdomain.responsibilities,
        is_confirmed=subdomain.is_confirmed,
        entity_count=entity_count,
        event_count=event_count,
        created_at=subdomain.created_at.isoformat(),
        updated_at=subdomain.updated_at.isoformat(),
    )


async def event_to_response(event: DomainEvent) -> DomainEventResponse:
    return DomainEventResponse(
        id=str(event.id),
        project_id=str(event.project_id),
        subdomain_id=str(event.subdomain_id) if event.subdomain_id else None,
        name=event.name,
        description=event.description,
        payload=event.payload,
        triggered_by=event.triggered_by,
        subscribers=event.subscribers,
        is_confirmed=event.is_confirmed,
        created_at=event.created_at.isoformat(),
        updated_at=event.updated_at.isoformat(),
    )


# ============================================================================
# Scaffold Generation
# ============================================================================

@router.post("/generate", response_model=DDDScaffoldResponse)
async def generate_ddd_scaffold(
    project_id: str,
    current_user: User = Depends(get_current_user),
    save: bool = True,
):
    """
    Generate DDD scaffold from intake content.
    
    Analyzes the project's intake phase (steps, artifacts, conversations)
    and generates a starting point for:
    - Domain Entities
    - Subdomains (bounded contexts)
    - Domain Events
    
    Set save=False to preview without saving.
    """
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if discovery is complete
    if _effective_phase(project.current_phase) == ProjectPhase.DISCOVERY:
        raise HTTPException(
            status_code=400,
            detail="Discovery phase should be completed before generating DDD scaffold"
        )
    
    # Generate scaffold
    scaffold = await ddd_generator.generate_from_project(project)
    
    if save and (scaffold["entities"] or scaffold["subdomains"] or scaffold["events"]):
        scaffold = await ddd_generator.save_scaffold(
            entities=scaffold["entities"],
            subdomains=scaffold["subdomains"],
            events=scaffold["events"],
        )
    
    return DDDScaffoldResponse(
        entities=[await entity_to_response(e) for e in scaffold["entities"]],
        subdomains=[await subdomain_to_response(s) for s in scaffold["subdomains"]],
        events=[await event_to_response(e) for e in scaffold["events"]],
        message=f"Generated {len(scaffold['entities'])} entities, {len(scaffold['subdomains'])} subdomains, {len(scaffold['events'])} events"
        + (" (saved)" if save else " (preview)"),
    )


# ============================================================================
# Domain Entities
# ============================================================================

@router.get("/entities", response_model=List[DomainEntityResponse])
async def list_domain_entities(
    project_id: str,
    current_user: User = Depends(get_current_user),
    subdomain_id: Optional[str] = None,
    confirmed_only: bool = False,
):
    """List domain entities for a project."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = {"project_id": project.id}
    if subdomain_id:
        query["subdomain_id"] = PydanticObjectId(subdomain_id)
    if confirmed_only:
        query["is_confirmed"] = True
    
    entities = await DomainEntity.find(query).to_list()
    return [await entity_to_response(e) for e in entities]


@router.post("/entities", response_model=DomainEntityResponse, status_code=201)
async def create_domain_entity(
    project_id: str,
    data: DomainEntityCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new domain entity."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    entity = DomainEntity(
        project_id=project.id,
        subdomain_id=PydanticObjectId(data.subdomain_id) if data.subdomain_id else None,
        name=data.name,
        description=data.description,
        properties=data.properties,
        relationships=data.relationships,
        is_aggregate_root=data.is_aggregate_root,
    )
    await entity.insert()
    
    return await entity_to_response(entity)


@router.patch("/entities/{entity_id}", response_model=DomainEntityResponse)
async def update_domain_entity(
    project_id: str,
    entity_id: str,
    data: DomainEntityUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a domain entity."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    entity = await DomainEntity.get(PydanticObjectId(entity_id))
    if not entity or entity.project_id != project.id:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "subdomain_id" in update_data:
        update_data["subdomain_id"] = PydanticObjectId(update_data["subdomain_id"]) if update_data["subdomain_id"] else None
    
    for key, value in update_data.items():
        setattr(entity, key, value)
    
    entity.updated_at = datetime.now(timezone.utc)
    await entity.save()
    
    return await entity_to_response(entity)


@router.delete("/entities/{entity_id}", status_code=204)
async def delete_domain_entity(
    project_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a domain entity."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    entity = await DomainEntity.get(PydanticObjectId(entity_id))
    if not entity or entity.project_id != project.id:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    await entity.delete()


# ============================================================================
# Subdomains
# ============================================================================

@router.get("/subdomains", response_model=List[SubdomainResponse])
async def list_subdomains(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """List subdomains for a project."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    subdomains = await Subdomain.find(Subdomain.project_id == project.id).to_list()
    return [await subdomain_to_response(s) for s in subdomains]


@router.post("/subdomains", response_model=SubdomainResponse, status_code=201)
async def create_subdomain(
    project_id: str,
    data: SubdomainCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new subdomain."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    subdomain = Subdomain(
        project_id=project.id,
        name=data.name,
        description=data.description,
        subdomain_type=data.subdomain_type,
        responsibilities=data.responsibilities,
    )
    await subdomain.insert()
    
    return await subdomain_to_response(subdomain)


@router.patch("/subdomains/{subdomain_id}", response_model=SubdomainResponse)
async def update_subdomain(
    project_id: str,
    subdomain_id: str,
    data: SubdomainUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a subdomain."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    subdomain = await Subdomain.get(PydanticObjectId(subdomain_id))
    if not subdomain or subdomain.project_id != project.id:
        raise HTTPException(status_code=404, detail="Subdomain not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(subdomain, key, value)
    
    subdomain.updated_at = datetime.now(timezone.utc)
    await subdomain.save()
    
    return await subdomain_to_response(subdomain)


@router.delete("/subdomains/{subdomain_id}", status_code=204)
async def delete_subdomain(
    project_id: str,
    subdomain_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a subdomain."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    subdomain = await Subdomain.get(PydanticObjectId(subdomain_id))
    if not subdomain or subdomain.project_id != project.id:
        raise HTTPException(status_code=404, detail="Subdomain not found")
    
    # Unlink entities and events from this subdomain
    await DomainEntity.find(DomainEntity.subdomain_id == subdomain.id).update(
        {"$set": {"subdomain_id": None}}
    )
    await DomainEvent.find(DomainEvent.subdomain_id == subdomain.id).update(
        {"$set": {"subdomain_id": None}}
    )
    
    await subdomain.delete()


# ============================================================================
# Domain Events
# ============================================================================

@router.get("/events", response_model=List[DomainEventResponse])
async def list_domain_events(
    project_id: str,
    current_user: User = Depends(get_current_user),
    subdomain_id: Optional[str] = None,
):
    """List domain events for a project."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = {"project_id": project.id}
    if subdomain_id:
        query["subdomain_id"] = PydanticObjectId(subdomain_id)
    
    events = await DomainEvent.find(query).to_list()
    return [await event_to_response(e) for e in events]


@router.post("/events", response_model=DomainEventResponse, status_code=201)
async def create_domain_event(
    project_id: str,
    data: DomainEventCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new domain event."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    event = DomainEvent(
        project_id=project.id,
        subdomain_id=PydanticObjectId(data.subdomain_id) if data.subdomain_id else None,
        name=data.name,
        description=data.description,
        payload=data.payload,
        triggered_by=data.triggered_by,
        subscribers=data.subscribers,
    )
    await event.insert()
    
    return await event_to_response(event)


@router.patch("/events/{event_id}", response_model=DomainEventResponse)
async def update_domain_event(
    project_id: str,
    event_id: str,
    data: DomainEventUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a domain event."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    event = await DomainEvent.get(PydanticObjectId(event_id))
    if not event or event.project_id != project.id:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "subdomain_id" in update_data:
        update_data["subdomain_id"] = PydanticObjectId(update_data["subdomain_id"]) if update_data["subdomain_id"] else None
    
    for key, value in update_data.items():
        setattr(event, key, value)
    
    event.updated_at = datetime.now(timezone.utc)
    await event.save()
    
    return await event_to_response(event)


@router.delete("/events/{event_id}", status_code=204)
async def delete_domain_event(
    project_id: str,
    event_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a domain event."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    event = await DomainEvent.get(PydanticObjectId(event_id))
    if not event or event.project_id != project.id:
        raise HTTPException(status_code=404, detail="Event not found")
    
    await event.delete()
