"""
Stats Routes.
API endpoints for global statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from backend.database import get_db
from backend.database.models import Project, Asset, Chunk, User
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
        user_projects = select(Project.id).where(Project.user_id == user.id).scalar_subquery()
        row = (await db.execute(
            select(
                select(func.count(Project.id)).where(Project.user_id == user.id).scalar_subquery().label('p'),
                select(func.count(Asset.id)).where(Asset.project_id.in_(select(Project.id).where(Project.user_id == user.id))).scalar_subquery().label('d'),
                select(func.count(Chunk.id)).where(Chunk.project_id.in_(select(Project.id).where(Project.user_id == user.id))).scalar_subquery().label('c'),
            )
        )).one()
        return {"projects": row.p or 0, "documents": row.d or 0, "chunks": row.c or 0}
    except Exception as e:
        if is_database_unavailable_error(e):
            raise db_unavailable_http_exception()
        raise HTTPException(status_code=500, detail=str(e))
