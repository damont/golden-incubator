import logging

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from api.schemas.orm.artifact import Artifact
from api.schemas.orm.conversation import Conversation
from api.schemas.orm.entity import Entity, EntityCounter
from api.schemas.orm.note import ActivityLog, Note
from api.schemas.orm.project import Project
from api.schemas.orm.user import User

logger = logging.getLogger(__name__)

DOCUMENT_MODELS = [
    User,
    Project,
    Conversation,
    Artifact,
    Entity,
    EntityCounter,
    Note,
    ActivityLog,
]


async def init_db(mongodb_url: str, db_name: str) -> AsyncIOMotorClient:
    """Initialize Beanie with all document models. Returns the Motor client."""
    client = AsyncIOMotorClient(mongodb_url)
    await init_beanie(database=client[db_name], document_models=DOCUMENT_MODELS)
    logger.info("Connected to MongoDB database: %s", db_name)
    return client
