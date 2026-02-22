"""
Steps - Low-level phases within high-level project phases.

Each step produces a markdown file output that captures the work done.
Entities (REQ, INSTR, etc.) are derived from these outputs.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from api.schemas.orm.project import ProjectPhase


class StepStatus(str, Enum):
    """Status of a step."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class Step(Document):
    """
    A low-level step within a high-level phase.
    
    Each step produces a markdown file that captures the work done.
    For example, in the Intake phase:
    - Step: Problem Discovery → problem_statement.md
    - Step: Stakeholder Analysis → stakeholders.md
    - Step: Initial Scope → scope.md
    """
    
    project_id: Indexed(PydanticObjectId)
    phase: ProjectPhase  # Which high-level phase this step belongs to
    
    # Step identification
    name: str  # e.g., "Problem Discovery"
    slug: str  # e.g., "problem-discovery" (used for file naming)
    description: Optional[str] = None
    order: int = 0  # Order within the phase
    
    # Status
    status: StepStatus = StepStatus.NOT_STARTED
    
    # Output file
    output_file: Optional[str] = None  # e.g., "intake/problem_statement.md"
    output_content: Optional[str] = None  # The markdown content
    
    # Tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "steps"


# Default steps for each phase
DEFAULT_PHASE_STEPS = {
    ProjectPhase.DISCOVERY: [
        {"name": "Problem Discovery", "slug": "problem-discovery", "description": "Understand the core problem being solved"},
        {"name": "Stakeholder Analysis", "slug": "stakeholders", "description": "Identify who will use and be affected by the system"},
        {"name": "Initial Scope", "slug": "scope", "description": "Define boundaries and high-level goals"},
        {"name": "Success Criteria", "slug": "success-criteria", "description": "Define what success looks like"},
        {"name": "MVP Requirements", "slug": "mvp-requirements", "description": "Identify essential launch-day features"},
    ],
    ProjectPhase.DOMAIN_DESIGN: [
        {"name": "Domain Model", "slug": "domain-model", "description": "DDD entities and aggregate roots"},
        {"name": "Entity Relationships", "slug": "entity-relationships", "description": "How entities relate to each other (ER diagram)"},
        {"name": "Subdomain Mapping", "slug": "subdomain-mapping", "description": "Bounded contexts and their responsibilities"},
        {"name": "Event Flows", "slug": "event-flows", "description": "Domain events and their triggers/subscribers"},
    ],
    ProjectPhase.BUILD: [
        {"name": "Project Setup", "slug": "project-setup", "description": "Repository, CI/CD, development environment"},
        {"name": "Core Implementation", "slug": "core-implementation", "description": "Build the core functionality"},
        {"name": "Testing", "slug": "testing", "description": "Unit, integration, and e2e tests"},
        {"name": "Documentation", "slug": "documentation", "description": "Code docs, API docs, README"},
    ],
    ProjectPhase.DEPLOY: [
        {"name": "Staging Deployment", "slug": "staging", "description": "Deploy to staging environment"},
        {"name": "Testing & QA", "slug": "qa", "description": "Final testing and quality assurance"},
        {"name": "Production Deployment", "slug": "production", "description": "Deploy to production"},
        {"name": "Monitoring Setup", "slug": "monitoring", "description": "Logging, alerts, dashboards"},
    ],
    ProjectPhase.HANDOFF: [
        {"name": "User Documentation", "slug": "user-docs", "description": "End-user guides and help"},
        {"name": "Admin Documentation", "slug": "admin-docs", "description": "Administration and maintenance guides"},
        {"name": "Training", "slug": "training", "description": "User and admin training materials"},
        {"name": "Support Setup", "slug": "support", "description": "Support channels and escalation"},
    ],
}
