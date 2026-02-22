import os

import pytest

os.environ.setdefault(
    "PAT_ENCRYPTION_KEY", "t8m6pyIPdFSDDjjLoyDBJGNF4Ez4zfoJ8Vl27INnCfA="
)

from api.schemas.orm.project import Project, PhaseHistoryEntry
from api.schemas.orm.user import User
from api.utils.auth import hash_password, create_access_token


@pytest.fixture
async def project_with_auth(client):
    user = User(
        username="artuser",
        email="art@example.com",
        hashed_password=hash_password("testpass123"),
    )
    await user.insert()
    token = create_access_token(str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    project = Project(
        name="Artifact Project",
        owner_id=user.id,
        phase_history=[PhaseHistoryEntry(phase="discovery", entered_at=now)],
    )
    await project.insert()
    return client, str(project.id)


@pytest.mark.anyio
async def test_create_artifact(project_with_auth):
    client, project_id = project_with_auth
    res = await client.post(f"/api/projects/{project_id}/artifacts", json={
        "artifact_type": "problem_statement",
        "title": "Problem Statement",
        "content": "# Problem\nUsers need a way to manage tasks.",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Problem Statement"
    assert data["artifact_type"] == "problem_statement"
    assert data["version"] == 1
    assert data["step_order"] == 1
    assert data["phase"] == "discovery"


@pytest.mark.anyio
async def test_list_artifacts(project_with_auth):
    client, project_id = project_with_auth
    await client.post(f"/api/projects/{project_id}/artifacts", json={
        "artifact_type": "problem_statement",
        "title": "PS",
        "content": "content",
    })
    await client.post(f"/api/projects/{project_id}/artifacts", json={
        "artifact_type": "user_stories",
        "title": "Stories",
        "content": "stories content",
    })
    res = await client.get(f"/api/projects/{project_id}/artifacts")
    assert res.status_code == 200
    assert len(res.json()) == 2


@pytest.mark.anyio
async def test_get_artifact(project_with_auth):
    client, project_id = project_with_auth
    create_res = await client.post(f"/api/projects/{project_id}/artifacts", json={
        "artifact_type": "requirements_doc",
        "title": "Requirements",
        "content": "# Requirements\n...",
    })
    artifact_id = create_res.json()["id"]
    res = await client.get(f"/api/projects/{project_id}/artifacts/{artifact_id}")
    assert res.status_code == 200
    assert res.json()["title"] == "Requirements"


@pytest.mark.anyio
async def test_update_artifact_versions(project_with_auth):
    client, project_id = project_with_auth
    create_res = await client.post(f"/api/projects/{project_id}/artifacts", json={
        "artifact_type": "problem_statement",
        "title": "PS v1",
        "content": "version 1",
    })
    artifact_id = create_res.json()["id"]
    assert create_res.json()["version"] == 1

    update_res = await client.put(f"/api/projects/{project_id}/artifacts/{artifact_id}", json={
        "artifact_type": "problem_statement",
        "title": "PS v2",
        "content": "version 2",
    })
    assert update_res.status_code == 200
    assert update_res.json()["version"] == 2
    assert update_res.json()["content"] == "version 2"


@pytest.mark.anyio
async def test_delete_artifact(project_with_auth):
    client, project_id = project_with_auth
    create_res = await client.post(f"/api/projects/{project_id}/artifacts", json={
        "artifact_type": "spec",
        "title": "Delete Me",
        "content": "to delete",
    })
    artifact_id = create_res.json()["id"]
    res = await client.delete(f"/api/projects/{project_id}/artifacts/{artifact_id}")
    assert res.status_code == 204

    res = await client.get(f"/api/projects/{project_id}/artifacts/{artifact_id}")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_artifacts_require_auth(client):
    res = await client.get("/api/projects/000000000000000000000000/artifacts")
    assert res.status_code == 401 or res.status_code == 403
