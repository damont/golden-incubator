import logging

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException

from api.schemas.dto.conversation import (
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
)
from api.schemas.orm.conversation import Conversation
from api.schemas.orm.project import Project
from api.schemas.orm.user import User
from api.services.agent_service import send_message
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


@router.post("/{project_id}/messages", response_model=MessageResponse)
async def post_message(
    project_id: str,
    data: SendMessageRequest,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        assistant_text, _ = await send_message(project_id, data.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MessageResponse(
        role="assistant",
        content=assistant_text,
        timestamp="",
    )


@router.get("/{project_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    project_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.get(PydanticObjectId(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    conversations = await Conversation.find(
        Conversation.project_id == project.id
    ).to_list()
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
