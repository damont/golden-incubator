import os

import pytest
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from api.main import app
from api.schemas.orm.document import RequirementsDocument
from api.schemas.orm.message import ChatMessage
from api.schemas.orm.session import Session
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
        document_models=[User, Session, ChatMessage, RequirementsDocument],
    )
    yield
    await client.drop_database(TEST_DB_NAME)
    client.close()


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
