import os

import pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault(
    "PAT_ENCRYPTION_KEY", "t8m6pyIPdFSDDjjLoyDBJGNF4Ez4zfoJ8Vl27INnCfA="
)

from api.schemas.orm.project import Project, PhaseHistoryEntry
from api.schemas.orm.user import User
from api.utils.auth import hash_password, create_access_token


@pytest.fixture
async def project_with_auth(client):
    """Create a user, project, and return authenticated client + project id."""
    user = User(
        username="projuser",
        email="proj@example.com",
        hashed_password=hash_password("testpass123"),
    )
    await user.insert()
    token = create_access_token(str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    project = Project(
        name="Test Project",
        description="Testing conversations",
        owner_id=user.id,
        phase_history=[PhaseHistoryEntry(phase="discovery", entered_at=now)],
    )
    await project.insert()
    return client, str(project.id)


@pytest.mark.anyio
async def test_send_message_with_mock_agent(project_with_auth):
    client, project_id = project_with_auth

    # Mock the Anthropic client
    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Tell me more about your project idea!"
    mock_response.content = [mock_text_block]

    with patch("api.services.agent_service.get_settings") as mock_settings:
        settings = MagicMock()
        settings.anthropic_api_key = "test-key"
        mock_settings.return_value = settings

        with patch("api.services.agent_service.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            res = await client.post(
                f"/api/projects/{project_id}/messages",
                json={"content": "I have an idea for a task management app"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["role"] == "assistant"
            assert "project" in data["content"].lower() or "tell" in data["content"].lower()


@pytest.mark.anyio
async def test_get_conversations(project_with_auth):
    client, project_id = project_with_auth
    res = await client.get(f"/api/projects/{project_id}/conversations")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.anyio
async def test_conversation_requires_auth(client):
    res = await client.get("/api/projects/000000000000000000000000/conversations")
    assert res.status_code == 401 or res.status_code == 403
