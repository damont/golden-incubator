import logging
from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from api.schemas.dto.conversation import (
    ConversationResponse,
    MessageResponse,
)
from api.schemas.orm.conversation import Conversation
from api.schemas.orm.project import Project, ProjectPhase
from api.schemas.orm.user import User
from api.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def conversation_to_response(conv: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=str(conv.id),
        project_id=str(conv.project_id),
        phase=conv.phase.value,
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                timestamp=m.timestamp.isoformat(),
            )
            for m in conv.messages
        ],
        summary=conv.summary,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.get("/{project_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    project_id: str,
    phase: Optional[str] = Query(None, description="Filter by phase (e.g. 'discovery', 'build')"),
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    query = Conversation.find(Conversation.project_id == project.id)
    if phase:
        try:
            phase_enum = ProjectPhase(phase)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid phase: {phase}")
        query = Conversation.find(
            Conversation.project_id == project.id,
            Conversation.phase == phase_enum,
        )
    conversations = await query.to_list()
    return [conversation_to_response(c) for c in conversations]


@router.get("/{project_id}/conversations/current", response_model=ConversationResponse)
async def get_current_conversation(
    project_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    conversation = await Conversation.find_one(
        Conversation.project_id == project.id,
        Conversation.phase == project.current_phase,
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="No conversation for current phase")

    return conversation_to_response(conversation)
