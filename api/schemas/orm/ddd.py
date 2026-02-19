"""
Domain-Driven Design models for architecture phase.

These models capture the DDD artifacts generated after intake:
- Domain Entities: Objects with identity in the domain
- Subdomains: Bounded contexts that group related functionality
- Domain Events: Things that happen in the domain
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field


class SubdomainType(str, Enum):
    """Types of subdomains in DDD."""
    CORE = "core"           # Competitive advantage, custom built
    SUPPORTING = "supporting"  # Necessary but not core
    GENERIC = "generic"     # Common problems, could use off-the-shelf


class DomainEntity(Document):
    """
    A domain entity in DDD - an object with identity.
    
    Examples: User, Order, Product, Invoice, Appointment
    """
    
    project_id: Indexed(PydanticObjectId)
    subdomain_id: Optional[PydanticObjectId] = None  # Which subdomain this belongs to
    
    name: str  # e.g., "User", "Order"
    description: str  # What this entity represents
    
    # Properties/attributes of this entity
    properties: List[dict] = []  # [{"name": "email", "type": "string", "required": true}, ...]
    
    # Relationships to other entities
    relationships: List[dict] = []  # [{"entity": "Order", "type": "has_many"}, ...]
    
    # Status
    is_aggregate_root: bool = False  # Is this an aggregate root?
    is_confirmed: bool = False  # Has the user confirmed this entity?
    
    # Source - which intake content suggested this entity
    source_text: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "domain_entities"


class Subdomain(Document):
    """
    A subdomain/bounded context in DDD.
    
    Groups related entities and functionality.
    Examples: Authentication, Billing, Inventory, Notifications
    """
    
    project_id: Indexed(PydanticObjectId)
    
    name: str  # e.g., "Authentication", "Billing"
    description: str  # What this subdomain handles
    subdomain_type: SubdomainType = SubdomainType.SUPPORTING
    
    # Key responsibilities
    responsibilities: List[str] = []  # ["User registration", "Login/logout", "Password reset"]
    
    # Status
    is_confirmed: bool = False
    
    # Source
    source_text: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "subdomains"


class DomainEvent(Document):
    """
    A domain event in DDD - something that happened.
    
    Events are past-tense actions that other parts of the system may react to.
    Examples: UserRegistered, OrderPlaced, PaymentProcessed, InventoryLow
    """
    
    project_id: Indexed(PydanticObjectId)
    subdomain_id: Optional[PydanticObjectId] = None  # Which subdomain triggers this
    
    name: str  # e.g., "UserRegistered", "OrderPlaced"
    description: str  # What this event represents
    
    # Event payload
    payload: List[dict] = []  # [{"name": "user_id", "type": "string"}, ...]
    
    # Triggered by which entity/action
    triggered_by: Optional[str] = None  # e.g., "User.register()"
    
    # What might react to this event
    subscribers: List[str] = []  # ["Send welcome email", "Create default settings"]
    
    # Status
    is_confirmed: bool = False
    
    # Source
    source_text: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "domain_events"


# All DDD models for Beanie initialization
DDD_MODELS = [DomainEntity, Subdomain, DomainEvent]
