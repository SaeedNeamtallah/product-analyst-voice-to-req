"""
Health Check Routes.
API endpoints for system health monitoring.
"""
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.services.redis_runtime import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    database: str
    llm_provider: str


class ReadinessResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    checks: dict


async def _database_readiness(db: AsyncSession) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "details": "Connection is healthy"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "not_ready", "details": f"DB check failed: {exc}"}


async def _redis_readiness() -> dict:
    if not settings.redis_enabled:
        return {"status": "degraded", "details": "REDIS_ENABLED=false"}

    redis = await get_redis()
    if redis is None:
        return {"status": "not_ready", "details": "Redis client unavailable"}

    try:
        pong = await redis.ping()
        if pong:
            return {"status": "ready", "details": "Ping successful"}
        return {"status": "not_ready", "details": "Ping failed"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "not_ready", "details": f"Redis check failed: {exc}"}


def _llm_config_readiness() -> dict:
    warnings_list, errors_list = settings.startup_issues()
    if errors_list:
        return {"status": "not_ready", "details": " | ".join(errors_list)}
    if warnings_list:
        return {"status": "degraded", "details": " | ".join(warnings_list)}
    return {"status": "ready", "details": "Provider config is valid"}


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


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Production-style readiness probe with component status details."""
    checks = {
        "database": await _database_readiness(db),
        "redis": await _redis_readiness(),
        "llm_config": _llm_config_readiness(),
    }

    overall = "ready"
    if any(item.get("status") == "not_ready" for item in checks.values()):
        overall = "not_ready"
    elif any(item.get("status") == "degraded" for item in checks.values()):
        overall = "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.environment,
        "checks": checks,
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
