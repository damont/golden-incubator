import json
import logging
from datetime import datetime, timezone

import jwt as pyjwt
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from api.config import get_settings
from api.schemas.dto.document import DocumentResponse
from api.schemas.dto.message import MessageResponse
from api.schemas.dto.session import SessionCreate, SessionResponse
from api.schemas.orm.document import RequirementsDocument
from api.schemas.orm.message import ChatMessage
from api.schemas.orm.session import Session
from api.schemas.orm.user import User
from api.services.requirements_agent import REQUIREMENTS_TEMPLATE, gather_requirements
from api.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────

def session_to_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=str(session.id),
        name=session.name,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


def message_to_response(msg: ChatMessage) -> MessageResponse:
    return MessageResponse(
        id=str(msg.id),
        session_id=str(msg.session_id),
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at.isoformat(),
    )


def document_to_response(doc: RequirementsDocument) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        session_id=str(doc.session_id),
        content=doc.content,
        version=doc.version,
        created_at=doc.created_at.isoformat(),
    )


async def get_latest_document(session_id: PydanticObjectId) -> RequirementsDocument | None:
    docs = await RequirementsDocument.find(
        RequirementsDocument.session_id == session_id,
    ).sort("-version").limit(1).to_list()
    return docs[0] if docs else None


async def verify_session_ownership(session_id: str, user: User) -> Session:
    session = await Session.get(PydanticObjectId(session_id))
    if not session or session.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def authenticate_ws_token(token: str) -> User:
    """Validate a JWT token for WebSocket connections (no HTTPBearer available)."""
    settings = get_settings()
    try:
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
    except pyjwt.InvalidTokenError:
        return None
    return await User.get(user_id)


# ── REST Endpoints ───────────────────────────────────────────────────

@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(data: SessionCreate, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    session = Session(
        name=data.name,
        owner_id=user.id,
        created_at=now,
        updated_at=now,
    )
    await session.insert()

    # Create initial document with empty template
    await RequirementsDocument(
        session_id=session.id,
        content=REQUIREMENTS_TEMPLATE,
        version=1,
        created_at=now,
    ).insert()

    logger.info("Session created: %s by user %s", session.name, user.id)
    return session_to_response(session)


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(user: User = Depends(get_current_user)):
    sessions = await Session.find(
        Session.owner_id == user.id,
    ).sort("-updated_at").to_list()
    return [session_to_response(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, user: User = Depends(get_current_user)):
    session = await verify_session_ownership(session_id, user)
    return session_to_response(session)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, user: User = Depends(get_current_user)):
    await verify_session_ownership(session_id, user)
    messages = await ChatMessage.find(
        ChatMessage.session_id == PydanticObjectId(session_id),
    ).sort("created_at").to_list()
    return [message_to_response(m) for m in messages]


@router.get("/{session_id}/document", response_model=DocumentResponse)
async def get_document(session_id: str, user: User = Depends(get_current_user)):
    await verify_session_ownership(session_id, user)
    doc = await get_latest_document(PydanticObjectId(session_id))
    if not doc:
        raise HTTPException(status_code=404, detail="No document found")
    return document_to_response(doc)


@router.get("/{session_id}/export")
async def export_document(session_id: str, user: User = Depends(get_current_user)):
    session = await verify_session_ownership(session_id, user)
    doc = await get_latest_document(PydanticObjectId(session_id))
    if not doc:
        raise HTTPException(status_code=404, detail="No document found")

    filename = f"{session.name.replace(' ', '-').lower()}-requirements.md"
    return Response(
        content=doc.content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, user: User = Depends(get_current_user)):
    session = await verify_session_ownership(session_id, user)
    sid = PydanticObjectId(session_id)
    # Cascade delete messages and documents
    await ChatMessage.find(ChatMessage.session_id == sid).delete()
    await RequirementsDocument.find(RequirementsDocument.session_id == sid).delete()
    await session.delete()
    logger.info("Session deleted: %s by user %s", session_id, user.id)


@router.post("/{session_id}/messages", response_model=dict)
async def send_message(session_id: str, data: dict, user: User = Depends(get_current_user)):
    """REST fallback for sending messages (non-WebSocket clients)."""
    session = await verify_session_ownership(session_id, user)
    sid = session.id
    content = data.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content required")

    now = datetime.now(timezone.utc)

    # Save user message
    user_msg = ChatMessage(session_id=sid, role="user", content=content, created_at=now)
    await user_msg.insert()

    # Build conversation history
    messages = await ChatMessage.find(
        ChatMessage.session_id == sid,
    ).sort("created_at").to_list()
    api_messages = [{"role": m.role, "content": m.content} for m in messages]

    # Get current document
    current_doc = await get_latest_document(sid)
    current_content = current_doc.content if current_doc else None

    # Call Claude
    result = await gather_requirements(api_messages, current_content)

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=sid, role="assistant", content=result["reply"], created_at=datetime.now(timezone.utc)
    )
    await assistant_msg.insert()

    # Save new document version
    new_version = (current_doc.version + 1) if current_doc else 1
    new_doc = RequirementsDocument(
        session_id=sid,
        content=result["document"],
        version=new_version,
        created_at=datetime.now(timezone.utc),
    )
    await new_doc.insert()

    # Update session timestamp
    session.updated_at = datetime.now(timezone.utc)
    await session.save()

    return {
        "message": message_to_response(assistant_msg).model_dump(),
        "document": document_to_response(new_doc).model_dump(),
    }


# ── WebSocket ────────────────────────────────────────────────────────

@router.websocket("/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # Authenticate via query param
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user = await authenticate_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Verify session ownership
    session = await Session.get(PydanticObjectId(session_id))
    if not session or session.owner_id != user.id:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    sid = session.id

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            if data.get("type") != "message":
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {data.get('type')}"})
                continue

            content = data.get("content", "").strip()
            if not content:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            now = datetime.now(timezone.utc)

            # Save user message
            user_msg = ChatMessage(session_id=sid, role="user", content=content, created_at=now)
            await user_msg.insert()
            await websocket.send_json({
                "type": "message_saved",
                "message": message_to_response(user_msg).model_dump(),
            })

            # Send thinking indicator
            await websocket.send_json({"type": "thinking"})

            try:
                # Build conversation history
                messages = await ChatMessage.find(
                    ChatMessage.session_id == sid,
                ).sort("created_at").to_list()
                api_messages = [{"role": m.role, "content": m.content} for m in messages]

                # Get current document
                current_doc = await get_latest_document(sid)
                current_content = current_doc.content if current_doc else None

                # Call Claude
                result = await gather_requirements(api_messages, current_content)

                # Save assistant message
                assistant_msg = ChatMessage(
                    session_id=sid,
                    role="assistant",
                    content=result["reply"],
                    created_at=datetime.now(timezone.utc),
                )
                await assistant_msg.insert()

                # Save new document version
                new_version = (current_doc.version + 1) if current_doc else 1
                new_doc = RequirementsDocument(
                    session_id=sid,
                    content=result["document"],
                    version=new_version,
                    created_at=datetime.now(timezone.utc),
                )
                await new_doc.insert()

                # Update session timestamp
                session.updated_at = datetime.now(timezone.utc)
                await session.save()

                # Send results
                await websocket.send_json({
                    "type": "assistant_message",
                    "message": message_to_response(assistant_msg).model_dump(),
                })
                await websocket.send_json({
                    "type": "document_update",
                    "document": document_to_response(new_doc).model_dump(),
                })

            except Exception as e:
                logger.error("Error processing message for session %s: %s", session_id, e)
                await websocket.send_json({
                    "type": "error",
                    "message": f"Failed to process message: {str(e)}",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
