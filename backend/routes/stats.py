"""
Stats Routes.
API endpoints for global statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from backend.database import get_db
from backend.database.models import Project, User
from backend.routes.auth import get_current_user
from backend.errors import is_database_unavailable_error, db_unavailable_http_exception

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/")
async def get_global_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics scoped to the current user's projects."""
    try:
        project_count = (await db.execute(
            select(func.count()).select_from(Project).where(Project.user_id == user.id)
        )).scalar() or 0

        return {"projects": project_count, "documents": 0, "transcripts": 0}
    except Exception as e:
        if is_database_unavailable_error(e):
            raise db_unavailable_http_exception()
        raise HTTPException(status_code=500, detail=str(e))
