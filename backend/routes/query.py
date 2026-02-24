"""
Query Routes.
API endpoints for querying project transcripts.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from backend.database import get_db
from backend.database.models import Project, User
from backend.routes.auth import get_current_user
from backend.controllers.query_controller import QueryController

router = APIRouter(tags=["Query"])
_query_controller = None


def get_query_controller() -> QueryController:
    global _query_controller
    if _query_controller is None:
        _query_controller = QueryController()
    return _query_controller


async def _verify_project_access(db: AsyncSession, project_id: int, user: User):
    """Verify the user owns this project."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user.id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")


# Request/Response Models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    language: str = Field(default="ar", pattern="^(ar|en)$")
    asset_id: Optional[int] = None


class SourceInfo(BaseModel):
    document_name: str
    chunk_index: int
    similarity: float
    asset_id: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    context_used: int


# Routes
@router.post("/projects/{project_id}/query", response_model=QueryResponse)
async def query_project(
    project_id: int,
    query_data: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question about project transcript content.
    Returns AI-generated answer with source references.
    """
    await _verify_project_access(db, project_id, user)
    try:
        query_controller = get_query_controller()
        result = await query_controller.answer_query(
            db=db,
            project_id=project_id,
            query=query_data.query,
            top_k=int(query_data.top_k or 5),
            language=query_data.language,
            asset_id=query_data.asset_id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/query/stream")
async def query_project_stream(
    project_id: int,
    query_data: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream an AI-generated answer via Server-Sent Events.
    Emits: source references event, then token events, then [DONE].
    """
    await _verify_project_access(db, project_id, user)
    query_controller = get_query_controller()
    top_k = int(query_data.top_k or 5)

    return StreamingResponse(
        query_controller.answer_query_stream(
            db=db,
            project_id=project_id,
            query=query_data.query,
            top_k=top_k,
            language=query_data.language,
            asset_id=query_data.asset_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
