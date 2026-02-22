import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from api.main import app
from api.schemas.orm.artifact import Artifact
from api.schemas.orm.conversation import Conversation
from api.schemas.orm.ddd import DomainEntity, Subdomain, DomainEvent
from api.schemas.orm.entity import Entity, EntityCounter
from api.schemas.orm.note import Note, ActivityLog
from api.schemas.orm.project import Project
from api.schemas.orm.step import Step
from api.schemas.orm.user import User
from api.utils.auth import hash_password, create_access_token

TEST_DB_NAME = "golden_incubator_test"
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_test_db():
    client = AsyncIOMotorClient(MONGODB_URL)
    await init_beanie(
        database=client[TEST_DB_NAME],
        document_models=[User, Project, Conversation, Artifact, Entity, EntityCounter, Note, ActivityLog, Step, DomainEntity, Subdomain, DomainEvent],
    )
    yield
    await client.drop_database(TEST_DB_NAME)
    client.close()


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Mock Redis so tests don't require a running Redis instance."""
    mock = MagicMock()
    mock.ping = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.hset = AsyncMock()
    mock.hgetall = AsyncMock(return_value={})
    mock.expire = AsyncMock()
    mock.delete = AsyncMock()
    mock.xadd = AsyncMock(return_value="1-0")
    mock.publish = AsyncMock()
    mock.close = AsyncMock()

    import api.services.redis as redis_mod
    monkeypatch.setattr(redis_mod, "_redis", mock)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def authenticated_client(client: AsyncClient):
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
    )
    await user.insert()
    token = create_access_token(str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
