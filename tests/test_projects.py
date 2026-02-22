import os

import pytest

# Set a valid Fernet key for tests before importing app modules
os.environ.setdefault(
    "PAT_ENCRYPTION_KEY", "t8m6pyIPdFSDDjjLoyDBJGNF4Ez4zfoJ8Vl27INnCfA="
)


@pytest.mark.anyio
async def test_create_project(authenticated_client):
    res = await authenticated_client.post("/api/projects/", json={
        "name": "Test Project",
        "description": "A test project",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test Project"
    assert data["current_phase"] == "discovery"
    assert len(data["phase_history"]) == 1
    assert data["phase_history"][0]["phase"] == "discovery"


@pytest.mark.anyio
async def test_create_project_with_github(authenticated_client):
    res = await authenticated_client.post("/api/projects/", json={
        "name": "GitHub Project",
        "github_repo_url": "https://github.com/test/repo",
        "github_pat": "ghp_test123",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["github_repo_url"] == "https://github.com/test/repo"


@pytest.mark.anyio
async def test_list_projects(authenticated_client):
    await authenticated_client.post("/api/projects/", json={"name": "Project 1"})
    await authenticated_client.post("/api/projects/", json={"name": "Project 2"})
    res = await authenticated_client.get("/api/projects/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_project(authenticated_client):
    create_res = await authenticated_client.post("/api/projects/", json={
        "name": "Get Me",
    })
    project_id = create_res.json()["id"]
    res = await authenticated_client.get(f"/api/projects/{project_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Get Me"


@pytest.mark.anyio
async def test_update_project(authenticated_client):
    create_res = await authenticated_client.post("/api/projects/", json={
        "name": "Original",
    })
    project_id = create_res.json()["id"]
    res = await authenticated_client.put(f"/api/projects/{project_id}", json={
        "name": "Updated",
    })
    assert res.status_code == 200
    assert res.json()["name"] == "Updated"


@pytest.mark.anyio
async def test_delete_project(authenticated_client):
    create_res = await authenticated_client.post("/api/projects/", json={
        "name": "Delete Me",
    })
    project_id = create_res.json()["id"]
    res = await authenticated_client.delete(f"/api/projects/{project_id}")
    assert res.status_code == 204

    res = await authenticated_client.get(f"/api/projects/{project_id}")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_project_requires_auth(client):
    res = await client.get("/api/projects/")
    assert res.status_code == 401 or res.status_code == 403


@pytest.mark.anyio
async def test_pat_not_in_response(authenticated_client):
    res = await authenticated_client.post("/api/projects/", json={
        "name": "PAT Test",
        "github_repo_url": "https://github.com/test/repo",
        "github_pat": "ghp_secret_token_123",
    })
    data = res.json()
    response_str = str(data)
    assert "ghp_secret_token_123" not in response_str
