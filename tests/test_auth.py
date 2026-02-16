import pytest


@pytest.mark.anyio
async def test_health_check(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_register(client):
    res = await client.post("/api/auth/register", json={
        "email": "new@example.com",
        "username": "newuser",
        "password": "password123",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data


@pytest.mark.anyio
async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "username": "dupuser",
        "password": "password123",
    })
    res = await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "username": "dupuser2",
        "password": "password123",
    })
    assert res.status_code == 400


@pytest.mark.anyio
async def test_login(client):
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "username": "loginuser",
        "password": "password123",
    })
    res = await client.post("/api/auth/login", json={
        "username": "loginuser",
        "password": "password123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.anyio
async def test_login_invalid_credentials(client):
    res = await client.post("/api/auth/login", json={
        "username": "nonexistent",
        "password": "wrong",
    })
    assert res.status_code == 401


@pytest.mark.anyio
async def test_me(authenticated_client):
    res = await authenticated_client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.anyio
async def test_me_no_token(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401 or res.status_code == 403
