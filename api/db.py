import logging

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from api.schemas.orm.document import RequirementsDocument
from api.schemas.orm.message import ChatMessage
from api.schemas.orm.session import Session
from api.schemas.orm.user import User

logger = logging.getLogger(__name__)

DOCUMENT_MODELS = [
    User,
    Session,
    ChatMessage,
    RequirementsDocument,
]


async def init_db(mongodb_url: str, db_name: str) -> AsyncIOMotorClient:
    """Initialize Beanie with all document models. Returns the Motor client."""
    client = AsyncIOMotorClient(mongodb_url)
    await init_beanie(database=client[db_name], document_models=DOCUMENT_MODELS)
    logger.info("Connected to MongoDB database: %s", db_name)
    return client
