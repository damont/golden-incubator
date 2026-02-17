import logging
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from api.config import get_settings
from api.routes import artifacts, auth, conversations, projects, entities, notes, progress
from api.schemas.orm.artifact import Artifact
from api.schemas.orm.conversation import Conversation
from api.schemas.orm.project import Project
from api.schemas.orm.user import User
from api.schemas.orm.entity import Entity, EntityCounter
from api.schemas.orm.note import Note, ActivityLog

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
        document_models=[
            User,
            Project,
            Conversation,
            Artifact,
            Entity,
            EntityCounter,
            Note,
            ActivityLog,
        ],
    )
    logger.info("Connected to MongoDB database: %s", settings.mongodb_db_name)
    yield
    client.close()
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="Golden Incubator API",
    description="AI-guided software development platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Project routes
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(conversations.router, prefix="/api/projects", tags=["conversations"])
app.include_router(artifacts.router, prefix="/api/projects", tags=["artifacts"])

# New: Entity, Notes, and Progress routes (no prefix - they include /api/projects/{project_id})
app.include_router(entities.router)
app.include_router(notes.router)
app.include_router(progress.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/schema")
async def get_schema():
    """Return OpenAPI schema."""
    return app.openapi()
