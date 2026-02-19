"""
DDD Scaffold Generator Service.

Analyzes intake phase outputs and generates a starting point for:
- Domain Entities
- Subdomains (bounded contexts)
- Domain Events

This gives users a foundation to review and refine rather than starting blank.
"""

from typing import List, Optional
import re

from beanie import PydanticObjectId

from api.schemas.orm.step import Step
from api.schemas.orm.ddd import (
    DomainEntity,
    Subdomain,
    DomainEvent,
    SubdomainType,
)
from api.schemas.orm.project import Project, ProjectPhase
from api.schemas.orm.artifact import Artifact
from api.schemas.orm.conversation import Conversation


class DDDGenerator:
    """
    Generates DDD artifacts from intake phase content.
    
    This is a heuristic-based generator that identifies likely:
    - Nouns → potential entities
    - Verbs → potential events
    - Functional areas → potential subdomains
    
    For production use, this would ideally be enhanced with LLM analysis.
    """
    
    # Common entity indicators
    ENTITY_PATTERNS = [
        r'\b(user|account|profile|member)\b',
        r'\b(order|purchase|transaction|payment)\b',
        r'\b(product|item|inventory|catalog)\b',
        r'\b(customer|client|vendor|supplier)\b',
        r'\b(message|notification|email|alert)\b',
        r'\b(appointment|booking|reservation|schedule)\b',
        r'\b(document|file|attachment|media)\b',
        r'\b(report|dashboard|analytics)\b',
        r'\b(setting|preference|configuration)\b',
        r'\b(role|permission|access)\b',
        r'\b(team|organization|company|group)\b',
        r'\b(project|task|issue|ticket)\b',
        r'\b(comment|review|feedback|rating)\b',
        r'\b(address|location|venue)\b',
        r'\b(invoice|receipt|billing)\b',
    ]
    
    # Common subdomain patterns
    SUBDOMAIN_PATTERNS = {
        'authentication': ['login', 'logout', 'password', 'auth', 'session', 'token', 'oauth', 'sso'],
        'user_management': ['user', 'profile', 'account', 'registration', 'onboarding'],
        'billing': ['payment', 'invoice', 'subscription', 'pricing', 'checkout', 'billing'],
        'notifications': ['email', 'notification', 'alert', 'message', 'sms', 'push'],
        'inventory': ['inventory', 'stock', 'warehouse', 'supply'],
        'ordering': ['order', 'cart', 'purchase', 'checkout'],
        'scheduling': ['appointment', 'booking', 'calendar', 'schedule', 'reservation'],
        'reporting': ['report', 'analytics', 'dashboard', 'metrics'],
        'content': ['content', 'cms', 'document', 'media', 'file'],
        'search': ['search', 'filter', 'query', 'browse'],
        'admin': ['admin', 'management', 'configuration', 'settings'],
    }
    
    # Event patterns (past tense actions)
    EVENT_PATTERNS = [
        (r'creat(e|ed|ing)', 'Created'),
        (r'updat(e|ed|ing)', 'Updated'),
        (r'delet(e|ed|ing)', 'Deleted'),
        (r'register(ed|ing)?', 'Registered'),
        (r'login|log in|logged in', 'LoggedIn'),
        (r'logout|log out|logged out', 'LoggedOut'),
        (r'submit(ted|ting)?', 'Submitted'),
        (r'approv(e|ed|ing)', 'Approved'),
        (r'reject(ed|ing)?', 'Rejected'),
        (r'cancel(led|ling)?', 'Cancelled'),
        (r'complet(e|ed|ing)', 'Completed'),
        (r'purchas(e|ed|ing)', 'Purchased'),
        (r'ship(ped|ping)?', 'Shipped'),
        (r'deliver(ed|ing)?', 'Delivered'),
        (r'pay|paid|paying', 'Paid'),
        (r'invit(e|ed|ing)', 'Invited'),
        (r'assign(ed|ing)?', 'Assigned'),
        (r'schedul(e|ed|ing)', 'Scheduled'),
        (r'notif(y|ied|ying)', 'Notified'),
    ]
    
    async def generate_from_project(self, project: Project) -> dict:
        """
        Generate DDD scaffold from a project's intake content.
        
        Returns:
            {
                "entities": [DomainEntity, ...],
                "subdomains": [Subdomain, ...],
                "events": [DomainEvent, ...],
            }
        """
        # Collect all intake content
        content = await self._collect_intake_content(project.id)
        
        if not content:
            return {"entities": [], "subdomains": [], "events": []}
        
        # Analyze and generate
        entities = await self._generate_entities(project.id, content)
        subdomains = await self._generate_subdomains(project.id, content)
        events = await self._generate_events(project.id, content, entities)
        
        return {
            "entities": entities,
            "subdomains": subdomains,
            "events": events,
        }
    
    async def _collect_intake_content(self, project_id: PydanticObjectId) -> str:
        """Collect all text content from intake phase."""
        content_parts = []
        
        # Get intake steps
        steps = await Step.find(
            Step.project_id == project_id,
            Step.phase == ProjectPhase.INTAKE,
        ).to_list()
        
        for step in steps:
            if step.output_content:
                content_parts.append(step.output_content)
        
        # Get intake artifacts
        artifacts = await Artifact.find(
            Artifact.project_id == project_id,
            Artifact.phase == ProjectPhase.INTAKE,
        ).to_list()
        
        for artifact in artifacts:
            if artifact.content:
                content_parts.append(artifact.content)
        
        # Get intake conversations
        conversations = await Conversation.find(
            Conversation.project_id == project_id,
            Conversation.phase == ProjectPhase.INTAKE,
        ).to_list()
        
        for conv in conversations:
            for msg in conv.messages:
                if msg.get('content'):
                    content_parts.append(msg['content'])
        
        return '\n\n'.join(content_parts)
    
    async def _generate_entities(
        self,
        project_id: PydanticObjectId,
        content: str,
    ) -> List[DomainEntity]:
        """Generate potential domain entities from content."""
        content_lower = content.lower()
        entities = []
        found_entities = set()
        
        for pattern in self.ENTITY_PATTERNS:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                # Normalize entity name
                entity_name = match.title()
                if entity_name in found_entities:
                    continue
                found_entities.add(entity_name)
                
                # Find context around the match
                idx = content_lower.find(match)
                context_start = max(0, idx - 100)
                context_end = min(len(content), idx + 100)
                source_text = content[context_start:context_end].strip()
                
                entity = DomainEntity(
                    project_id=project_id,
                    name=entity_name,
                    description=f"Represents a {entity_name.lower()} in the system",
                    source_text=source_text,
                )
                entities.append(entity)
        
        return entities
    
    async def _generate_subdomains(
        self,
        project_id: PydanticObjectId,
        content: str,
    ) -> List[Subdomain]:
        """Generate potential subdomains from content."""
        content_lower = content.lower()
        subdomains = []
        
        for subdomain_name, keywords in self.SUBDOMAIN_PATTERNS.items():
            # Check if any keywords appear in content
            keyword_hits = [kw for kw in keywords if kw in content_lower]
            
            if keyword_hits:
                # Determine subdomain type based on common patterns
                if subdomain_name in ['authentication', 'user_management']:
                    sd_type = SubdomainType.GENERIC
                elif subdomain_name in ['billing', 'ordering']:
                    sd_type = SubdomainType.CORE
                else:
                    sd_type = SubdomainType.SUPPORTING
                
                subdomain = Subdomain(
                    project_id=project_id,
                    name=subdomain_name.replace('_', ' ').title(),
                    description=f"Handles {subdomain_name.replace('_', ' ')} functionality",
                    subdomain_type=sd_type,
                    responsibilities=[f"Manage {kw}" for kw in keyword_hits[:3]],
                )
                subdomains.append(subdomain)
        
        return subdomains
    
    async def _generate_events(
        self,
        project_id: PydanticObjectId,
        content: str,
        entities: List[DomainEntity],
    ) -> List[DomainEvent]:
        """Generate potential domain events from content and entities."""
        content_lower = content.lower()
        events = []
        found_events = set()
        
        # Generate events based on entities + common actions
        for entity in entities:
            entity_name = entity.name
            
            for pattern, event_suffix in self.EVENT_PATTERNS:
                if re.search(pattern, content_lower):
                    event_name = f"{entity_name}{event_suffix}"
                    
                    if event_name in found_events:
                        continue
                    found_events.add(event_name)
                    
                    event = DomainEvent(
                        project_id=project_id,
                        name=event_name,
                        description=f"Triggered when a {entity_name.lower()} is {event_suffix.lower()}",
                        triggered_by=f"{entity_name}.{event_suffix.lower()}()",
                        payload=[{"name": f"{entity_name.lower()}_id", "type": "string"}],
                    )
                    events.append(event)
        
        return events
    
    async def save_scaffold(
        self,
        entities: List[DomainEntity],
        subdomains: List[Subdomain],
        events: List[DomainEvent],
    ) -> dict:
        """Save all generated DDD artifacts to database."""
        saved = {"entities": [], "subdomains": [], "events": []}
        
        for subdomain in subdomains:
            await subdomain.insert()
            saved["subdomains"].append(subdomain)
        
        # Create a subdomain lookup for entity assignment
        subdomain_lookup = {s.name.lower(): s for s in saved["subdomains"]}
        
        for entity in entities:
            # Try to assign to a subdomain
            entity_name_lower = entity.name.lower()
            for sd_name, sd in subdomain_lookup.items():
                if entity_name_lower in sd_name or sd_name.split()[0] in entity_name_lower:
                    entity.subdomain_id = sd.id
                    break
            
            await entity.insert()
            saved["entities"].append(entity)
        
        for event in events:
            await event.insert()
            saved["events"].append(event)
        
        return saved


# Singleton instance
ddd_generator = DDDGenerator()
