import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.db import init_db
from api.routes import auth, sessions

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

    yield

    client.close()
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title="Golden Incubator API",
    description="Collaborative requirements gathering tool",
    version="1.0.0",
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

# Session routes (REST + WebSocket)
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/schema")
async def get_schema():
    """Return OpenAPI schema."""
    return app.openapi()
