"""
Health Check Routes.
API endpoints for system health monitoring.
"""
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    database: str
    vector_db: str
    llm_provider: str
    vector_db_provider: str


async def _check_qdrant() -> str:
    """Ping the Qdrant /healthz endpoint."""
    try:
        import asyncio
        parsed = urlparse(settings.qdrant_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6333
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=3.0,
        )
        writer.close()
        await writer.wait_closed()
        return "connected"
    except Exception as exc:
        logger.debug("Qdrant health check failed: %s", exc)
        return "disconnected"


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check system health status including database and vector DB."""
    # --- Database ---
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # --- Vector DB ---
    if settings.vector_db_provider == "pgvector":
        vector_db_status = db_status  # same underlying PostgreSQL
    elif settings.vector_db_provider == "qdrant":
        vector_db_status = await _check_qdrant()
    else:
        vector_db_status = "unchecked"

    # --- Overall status ---
    if db_status == "disconnected":
        overall = "unhealthy"
    elif vector_db_status == "disconnected":
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "database": db_status,
        "vector_db": vector_db_status,
        "llm_provider": settings.llm_provider,
        "vector_db_provider": settings.vector_db_provider,
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health"
    }
