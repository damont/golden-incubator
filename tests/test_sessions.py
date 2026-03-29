import pytest

from api.schemas.orm.document import RequirementsDocument
from api.schemas.orm.message import ChatMessage


@pytest.mark.anyio
async def test_create_session(authenticated_client):
    res = await authenticated_client.post("/api/sessions/", json={"name": "Test App"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test App"
    assert "id" in data


@pytest.mark.anyio
async def test_list_sessions(authenticated_client):
    await authenticated_client.post("/api/sessions/", json={"name": "Session A"})
    await authenticated_client.post("/api/sessions/", json={"name": "Session B"})
    res = await authenticated_client.get("/api/sessions/")
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) >= 2


@pytest.mark.anyio
async def test_get_session(authenticated_client):
    create_res = await authenticated_client.post("/api/sessions/", json={"name": "My Session"})
    session_id = create_res.json()["id"]

    res = await authenticated_client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "My Session"


@pytest.mark.anyio
async def test_get_document(authenticated_client):
    create_res = await authenticated_client.post("/api/sessions/", json={"name": "Doc Test"})
    session_id = create_res.json()["id"]

    res = await authenticated_client.get(f"/api/sessions/{session_id}/document")
    assert res.status_code == 200
    doc = res.json()
    assert doc["version"] == 1
    assert "## Overview" in doc["content"]


@pytest.mark.anyio
async def test_get_messages_empty(authenticated_client):
    create_res = await authenticated_client.post("/api/sessions/", json={"name": "Empty Chat"})
    session_id = create_res.json()["id"]

    res = await authenticated_client.get(f"/api/sessions/{session_id}/messages")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.anyio
async def test_delete_session(authenticated_client):
    create_res = await authenticated_client.post("/api/sessions/", json={"name": "To Delete"})
    session_id = create_res.json()["id"]

    res = await authenticated_client.delete(f"/api/sessions/{session_id}")
    assert res.status_code == 204

    # Verify it's gone
    res = await authenticated_client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_export_document(authenticated_client):
    create_res = await authenticated_client.post("/api/sessions/", json={"name": "Export Test"})
    session_id = create_res.json()["id"]

    res = await authenticated_client.get(f"/api/sessions/{session_id}/export")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert "## Overview" in res.text


@pytest.mark.anyio
async def test_session_not_found(authenticated_client):
    res = await authenticated_client.get("/api/sessions/000000000000000000000000")
    assert res.status_code == 404
