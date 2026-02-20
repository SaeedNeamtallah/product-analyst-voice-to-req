"""
Interview routes for guided requirements questions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.database.models import Project, User
from backend.routes.auth import get_current_user
from backend.services.interview_service import InterviewService
from backend.services.telemetry_service import TelemetryService

router = APIRouter(tags=["Interview"])
_interview_service = None


def get_interview_service() -> InterviewService:
    global _interview_service
    if _interview_service is None:
        _interview_service = InterviewService()
    return _interview_service


class InterviewRequest(BaseModel):
    language: str = Field(default="ar", pattern="^(ar|en)$")
    last_summary: Optional[Dict[str, List[str]]] = None
    last_coverage: Optional[Dict[str, float]] = None


class InterviewResponse(BaseModel):
    question: str
    stage: str
    done: bool
    suggested_answers: List[str] | None = None
    summary: Any = None
    coverage: dict | None = None
    signals: dict | None = None
    live_patch: dict | None = None
    cycle_trace: dict | None = None
    topic_navigation: dict | None = None


class InterviewDraftPayload(BaseModel):
    summary: Optional[Dict[str, List[str]]] = None
    coverage: Optional[Dict[str, float]] = None
    signals: Optional[Dict[str, Any]] = None
    livePatch: Optional[Dict[str, Any]] = None
    cycleTrace: Optional[Dict[str, Any]] = None
    topicNavigation: Optional[Dict[str, Any]] = None
    stage: str = "discovery"
    mode: bool = False
    lastAssistantQuestion: str = ""
    savedAt: Optional[str] = None
    lang: str = Field(default="ar", pattern="^(ar|en)$")


def _get_project_interview_draft(project: Project) -> Optional[Dict[str, Any]]:
    metadata = project.extra_metadata if isinstance(project.extra_metadata, dict) else {}
    draft = metadata.get("interview_draft")
    return draft if isinstance(draft, dict) else None


async def _get_user_project(db: AsyncSession, project_id: int, user: User) -> Project:
    """Fetch project scoped to the authenticated user. Raises 404 if not found."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user.id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/interview/next", response_model=InterviewResponse)
async def next_question(
    project_id: int,
    payload: InterviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_project(db, project_id, user)
    service = get_interview_service()
    result = await service.get_next_question(
        db, project_id, payload.language,
        last_summary=payload.last_summary,
        last_coverage=payload.last_coverage,
    )
    await TelemetryService.record_interview_turn(db=db, project_id=project_id, result=result)
    await db.commit()
    return result


@router.get("/projects/{project_id}/interview/telemetry")
async def get_interview_telemetry(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_project(db, project_id, user)
    report = await TelemetryService.get_report(db=db, project_id=project_id)
    return report


@router.get("/projects/{project_id}/interview/draft")
async def get_interview_draft(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(db, project_id, user)
    return {"draft": _get_project_interview_draft(project)}


@router.post("/projects/{project_id}/interview/draft")
async def save_interview_draft(
    project_id: int,
    payload: InterviewDraftPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(db, project_id, user)
    metadata = dict(project.extra_metadata or {})
    metadata["interview_draft"] = payload.model_dump()
    project.extra_metadata = metadata
    await db.commit()
    return {"success": True, "draft": metadata["interview_draft"]}


@router.delete("/projects/{project_id}/interview/draft")
async def clear_interview_draft(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(db, project_id, user)
    metadata = dict(project.extra_metadata or {})
    metadata.pop("interview_draft", None)
    project.extra_metadata = metadata
    await db.commit()
    return {"success": True}
