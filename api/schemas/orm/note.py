"""
Project notes and activity log.

Captures all notes, decisions, and activities throughout the project lifecycle.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from api.schemas.orm.project import ProjectPhase


class NoteType(str, Enum):
    """Types of notes that can be logged."""
    USER_NOTE = "user_note"           # Note added by user
    AGENT_NOTE = "agent_note"         # Note added by AI agent
    SYSTEM_NOTE = "system_note"       # Automated system note
    PHASE_CHANGE = "phase_change"     # Phase transition record
    DECISION = "decision"             # Important decision made
    CLARIFICATION = "clarification"   # Clarification from user
    FEEDBACK = "feedback"             # User feedback on something


class Note(Document):
    """
    A note or activity log entry for a project.
    
    Notes capture important information, decisions, and context
    throughout the project lifecycle.
    """
    
    project_id: Indexed(PydanticObjectId)
    phase: ProjectPhase  # Which phase this note was created in
    
    note_type: NoteType
    content: str  # The note content (markdown supported)
    
    # Optional references
    artifact_id: Optional[PydanticObjectId] = None
    conversation_id: Optional[PydanticObjectId] = None
    entity_ids: List[PydanticObjectId] = []  # Related entities
    
    # For phase changes
    from_phase: Optional[ProjectPhase] = None
    to_phase: Optional[ProjectPhase] = None
    
    # Metadata
    tags: List[str] = []
    pinned: bool = False  # Important notes can be pinned
    
    created_by: str  # user_id or "agent" or "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "notes"


class ActivityLog(Document):
    """
    Detailed activity log for audit trail.
    
    Logs every significant action in the project for full traceability.
    """
    
    project_id: Indexed(PydanticObjectId)
    phase: ProjectPhase
    
    action: str  # e.g., "entity_created", "artifact_updated", "phase_advanced"
    actor: str  # user_id or "agent" or "system"
    
    # What was affected
    target_type: Optional[str] = None  # "entity", "artifact", "conversation", etc.
    target_id: Optional[PydanticObjectId] = None
    
    # Details
    details: dict = {}  # Action-specific details
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "activity_logs"
