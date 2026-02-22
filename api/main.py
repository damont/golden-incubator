import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.db import init_db
from api.routes import artifacts, auth, conversations, entities, jobs, notes, progress, projects, steps, ddd
from api.services.redis import close_redis, init_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Initialize MongoDB
    client = await init_db(settings.mongodb_url, settings.mongodb_db_name)

    # Initialize Redis
    await init_redis(settings.redis_url)

    # Initialize file storage
    from api.services.storage import get_storage
    get_storage()
    logger.info("Storage backend initialized (upload_dir: %s)", settings.upload_dir)

    yield

    await close_redis()
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

# Job routes
app.include_router(jobs.router, prefix="/api", tags=["jobs"])

# Entity, Notes, Progress, Steps, and DDD routes (no prefix - they include /api/projects/{project_id})
app.include_router(entities.router)
app.include_router(notes.router)
app.include_router(progress.router)
app.include_router(steps.router)
app.include_router(ddd.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/schema")
async def get_schema():
    """Return OpenAPI schema."""
    return app.openapi()
