"""
Health Check Routes.
API endpoints for system health monitoring.
"""
import logging

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
    llm_provider: str


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check system health status including database and LLM provider."""
    # --- Database ---
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # --- Overall status ---
    if db_status == "disconnected":
        overall = "unhealthy"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "database": db_status,
        "llm_provider": settings.llm_provider,
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
