"""
Entity management routes.

Handles CRUD operations for semantic entities extracted from project artifacts.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from beanie import PydanticObjectId

from api.schemas.orm.entity import Entity, EntityCounter, EntityType, EntityStatus
from api.schemas.orm.project import Project
from api.schemas.orm.note import ActivityLog
from api.utils.auth import get_current_user
from api.schemas.orm.user import User
from api.services.markdown_parser import markdown_parser

router = APIRouter(prefix="/api/projects/{project_id}/entities", tags=["entities"])


# ============================================================================
# DTOs
# ============================================================================

class EntityCreate(BaseModel):
    entity_type: EntityType
    title: str = Field(..., min_length=1, max_length=200)
    description: str
    tags: List[str] = []
    priority: Optional[int] = Field(None, ge=1, le=5)
    parent_id: Optional[str] = None
    source_text: Optional[str] = None


class EntityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[EntityStatus] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


class EntityResponse(BaseModel):
    id: str
    project_id: str
    entity_type: str
    reference_id: str
    status: str
    title: str
    description: str
    tags: List[str]
    priority: Optional[int]
    source_text: str
    created_by: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ParseRequest(BaseModel):
    content: str
    auto_create: bool = False  # If true, create entities directly


class ParseResponse(BaseModel):
    entities: List[EntityResponse]
    created_count: int


# ============================================================================
# Helpers
# ============================================================================

async def get_or_create_counter(project_id: PydanticObjectId) -> EntityCounter:
    """Get or create entity counter for a project."""
    counter = await EntityCounter.find_one(EntityCounter.project_id == project_id)
    if not counter:
        counter = EntityCounter(project_id=project_id, counters={})
        await counter.insert()
    return counter


def entity_to_response(entity: Entity) -> EntityResponse:
    """Convert Entity to response model."""
    return EntityResponse(
        id=str(entity.id),
        project_id=str(entity.project_id),
        entity_type=entity.entity_type.value,
        reference_id=entity.reference_id,
        status=entity.status.value,
        title=entity.title,
        description=entity.description,
        tags=entity.tags,
        priority=entity.priority,
        source_text=entity.source_text,
        created_by=entity.created_by,
        created_at=entity.created_at.isoformat(),
        updated_at=entity.updated_at.isoformat(),
    )


# ============================================================================
# Routes
# ============================================================================

@router.get("", response_model=List[EntityResponse])
async def list_entities(
    project_id: str,
    current_user: User = Depends(get_current_user),
    entity_type: Optional[EntityType] = Query(None),
    status: Optional[EntityStatus] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List entities for a project with optional filters."""
    # Verify project access
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Build query
    query = {"project_id": project.id}
    if entity_type:
        query["entity_type"] = entity_type
    if status:
        query["status"] = status
    if tag:
        query["tags"] = tag
    
    entities = await Entity.find(query).skip(offset).limit(limit).to_list()
    return [entity_to_response(e) for e in entities]


@router.get("/summary")
async def get_entity_summary(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get summary counts of entities by type and status."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Aggregate counts
    pipeline = [
        {"$match": {"project_id": project.id}},
        {"$group": {
            "_id": {"type": "$entity_type", "status": "$status"},
            "count": {"$sum": 1}
        }}
    ]
    
    results = await Entity.aggregate(pipeline).to_list()
    
    # Organize by type
    summary = {}
    for r in results:
        entity_type = r["_id"]["type"]
        status = r["_id"]["status"]
        if entity_type not in summary:
            summary[entity_type] = {"total": 0, "by_status": {}}
        summary[entity_type]["by_status"][status] = r["count"]
        summary[entity_type]["total"] += r["count"]
    
    return {
        "project_id": project_id,
        "current_phase": project.current_phase.value,
        "entities": summary,
    }


@router.post("", response_model=EntityResponse, status_code=201)
async def create_entity(
    project_id: str,
    data: EntityCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new entity manually."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get next reference ID
    counter = await get_or_create_counter(project.id)
    reference_id = counter.next_id(data.entity_type)
    await counter.save()
    
    # Create entity
    entity = Entity(
        project_id=project.id,
        entity_type=data.entity_type,
        reference_id=reference_id,
        title=data.title,
        description=data.description,
        tags=data.tags,
        priority=data.priority,
        source_text=data.source_text or data.description,
        parent_id=PydanticObjectId(data.parent_id) if data.parent_id else None,
        created_by=str(current_user.id),
    )
    await entity.insert()
    
    # Log activity
    await ActivityLog(
        project_id=project.id,
        phase=project.current_phase,
        action="entity_created",
        actor=str(current_user.id),
        target_type="entity",
        target_id=entity.id,
        details={"entity_type": data.entity_type.value, "reference_id": reference_id},
    ).insert()
    
    return entity_to_response(entity)


@router.post("/parse", response_model=ParseResponse)
async def parse_content(
    project_id: str,
    data: ParseRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Parse markdown content and extract entities.
    
    If auto_create is True, entities are created in the database.
    Otherwise, returns preview of what would be created.
    """
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Parse content
    parsed = markdown_parser.parse(data.content)
    
    created_entities = []

    if data.auto_create and parsed:
        counter = await get_or_create_counter(project.id)

        for p in parsed:
            reference_id = counter.next_id(p.entity_type)

            entity = Entity(
                project_id=project.id,
                entity_type=p.entity_type,
                reference_id=reference_id,
                title=p.title,
                description=p.description,
                tags=p.tags,
                priority=p.priority,
                source_text=p.source_text,
                source_line=p.source_line,
                created_by="parser",
            )
            await entity.insert()
            created_entities.append(entity)

        await counter.save()

        # Log activity
        await ActivityLog(
            project_id=project.id,
            phase=project.current_phase,
            action="entities_parsed",
            actor=str(current_user.id),
            details={"count": len(created_entities)},
        ).insert()
    else:
        # Preview mode - create temporary response objects
        for i, p in enumerate(parsed):
            temp_entity = Entity(
                project_id=project.id,
                entity_type=p.entity_type,
                reference_id=f"{p.entity_type.value}-NEW",
                title=p.title,
                description=p.description,
                tags=p.tags,
                priority=p.priority,
                source_text=p.source_text,
                source_line=p.source_line,
                created_by="parser",
            )
            created_entities.append(temp_entity)
    
    return ParseResponse(
        entities=[entity_to_response(e) for e in created_entities],
        created_count=len(created_entities) if data.auto_create else 0,
    )


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    project_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a single entity by ID."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    entity = await Entity.get(PydanticObjectId(entity_id))
    if not entity or entity.project_id != project.id:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return entity_to_response(entity)


@router.patch("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    project_id: str,
    entity_id: str,
    data: EntityUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update an entity."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    entity = await Entity.get(PydanticObjectId(entity_id))
    if not entity or entity.project_id != project.id:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    old_status = entity.status
    
    for key, value in update_data.items():
        setattr(entity, key, value)
    
    from datetime import datetime, timezone
    entity.updated_at = datetime.now(timezone.utc)
    await entity.save()
    
    # Log status changes
    if data.status and data.status != old_status:
        await ActivityLog(
            project_id=project.id,
            phase=project.current_phase,
            action="entity_status_changed",
            actor=str(current_user.id),
            target_type="entity",
            target_id=entity.id,
            details={"from": old_status.value, "to": data.status.value},
        ).insert()
    
    return entity_to_response(entity)


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    project_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete an entity."""
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    entity = await Entity.get(PydanticObjectId(entity_id))
    if not entity or entity.project_id != project.id:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    reference_id = entity.reference_id
    await entity.delete()
    
    # Log activity
    await ActivityLog(
        project_id=project.id,
        phase=project.current_phase,
        action="entity_deleted",
        actor=str(current_user.id),
        details={"reference_id": reference_id},
    ).insert()
