import logging
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from api.config import get_settings
from api.routes import artifacts, auth, conversations, projects
from api.schemas.orm.artifact import Artifact
from api.schemas.orm.conversation import Conversation
from api.schemas.orm.project import Project
from api.schemas.orm.user import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    await init_beanie(
        database=client[settings.mongodb_db_name],
        document_models=[User, Project, Conversation, Artifact],
    )
    logger.info("Connected to MongoDB database: %s", settings.mongodb_db_name)
    yield
    client.close()
    logger.info("Disconnected from MongoDB")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(conversations.router, prefix="/api/projects", tags=["conversations"])
app.include_router(artifacts.router, prefix="/api/projects", tags=["artifacts"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
