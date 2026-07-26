"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.services.ai_service import ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_tables:
        await init_db()
    else:
        logger.info("auto_create_tables=False — run `alembic upgrade head` to migrate.")
    logger.info(
        "Started %s | LLM: %s",
        settings.app_name,
        f"enabled ({settings.llm_model})" if ai.enabled else "disabled (offline fallback)",
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "AI Career Coach for Python Backend Engineers — resume analysis, "
        "question generation and text mock interviews powered by Claude."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Token is sent via the Authorization header (not cookies), so credentials
    # mode is off — this lets allow_origins="*" return a valid CORS response.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["health"])
async def root() -> dict:
    return {
        "app": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "llm_enabled": ai.enabled,
    }


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
