"""
Semantic entities extracted from markdown documents.

These represent structured data parsed from natural language artifacts,
using markers like REQ:, INSTR:, NOTE:, etc.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from api.schemas.orm.project import ProjectPhase


class EntityType(str, Enum):
    """Types of semantic entities we extract from markdown."""
    REQUIREMENT = "REQ"           # A requirement the software must fulfill
    INSTRUCTION = "INSTR"         # An instruction for the user to follow
    DECISION = "DEC"              # A decision that was made
    QUESTION = "Q"                # An open question needing resolution
    ASSUMPTION = "ASSUME"         # An assumption being made
    CONSTRAINT = "CONST"          # A constraint or limitation
    RISK = "RISK"                 # An identified risk
    TODO = "TODO"                 # A task to complete
    NOTE = "NOTE"                 # A general note


class EntityStatus(str, Enum):
    """Status of an entity."""
    DRAFT = "draft"               # Initial extraction, needs review
    CONFIRMED = "confirmed"       # User confirmed this is correct
    REJECTED = "rejected"         # User marked as incorrect/invalid
    COMPLETED = "completed"       # For actionable items (INSTR, TODO)
    SUPERSEDED = "superseded"     # Replaced by a newer version


class Entity(Document):
    """
    A semantic entity extracted from project artifacts.
    
    Entities are parsed from markdown content using markers like:
    - REQ: User must be able to login with email
    - INSTR: Create a new GitHub repository
    - NOTE: Client prefers a minimalist UI
    """
    
    project_id: Indexed(PydanticObjectId)
    artifact_id: Optional[PydanticObjectId] = None  # Source artifact, if any
    conversation_id: Optional[PydanticObjectId] = None  # Source conversation, if any
    
    entity_type: Indexed(EntityType)
    status: EntityStatus = EntityStatus.DRAFT
    phase: ProjectPhase  # Which phase this entity belongs to
    
    # The entity content
    reference_id: str  # e.g., "REQ-001", "INSTR-003"
    title: str  # Short summary
    description: str  # Full description
    
    # Categorization
    tags: List[str] = []
    priority: Optional[int] = Field(None, ge=1, le=5)  # 1=highest, 5=lowest
    
    # Traceability
    parent_id: Optional[PydanticObjectId] = None  # For hierarchical entities
    related_ids: List[PydanticObjectId] = []  # Related entities
    
    # Source tracking
    source_text: str  # Original text that was parsed
    source_line: Optional[int] = None  # Line number in source
    
    # Metadata
    created_by: str  # user_id or "agent" or "parser"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "entities"


class EntityCounter(Document):
    """
    Tracks the next ID for each entity type per project.
    Ensures unique sequential IDs like REQ-001, REQ-002, etc.
    """
    
    project_id: Indexed(PydanticObjectId, unique=True)
    counters: dict[str, int] = {}  # {"REQ": 5, "INSTR": 3, ...}
    
    class Settings:
        name = "entity_counters"
    
    def next_id(self, entity_type: EntityType) -> str:
        """Get next ID for an entity type and increment counter."""
        key = entity_type.value
        current = self.counters.get(key, 0)
        self.counters[key] = current + 1
        return f"{key}-{str(current + 1).zfill(3)}"
