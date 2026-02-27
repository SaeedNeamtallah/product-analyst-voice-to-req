"""
Interview routes for guided requirements questions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db, async_session_maker
from backend.database.models import Project, User, SRSDraft
from backend.routes.auth import get_current_user
from backend.services.interview_service import InterviewService
from backend.services.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interview"])
_interview_service = None


def get_interview_service() -> InterviewService:
    global _interview_service
    if _interview_service is None:
        _interview_service = InterviewService()
    return _interview_service


class InterviewRequest(BaseModel):
    language: str = Field(default="ar", pattern="^(ar|en)$")
    last_summary: Optional[Dict[str, Any]] = None
    last_coverage: Optional[Dict[str, Any]] = None
    aim_for_100: bool = Field(default=False)


def _normalize_last_summary(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, List[str]]]:
    if not isinstance(value, dict):
        return None

    normalized: Dict[str, List[str]] = {}
    for key, raw_items in value.items():
        area = str(key).strip()
        if not area:
            continue
        if not isinstance(raw_items, list):
            continue
        items = [str(item).strip() for item in raw_items if str(item).strip()]
        if items:
            normalized[area] = items

    return normalized or None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_last_coverage(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    if not isinstance(value, dict):
        return None

    normalized: Dict[str, float] = {}
    for key, raw_value in value.items():
        area = str(key).strip()
        if not area:
            continue
        parsed = _to_float(raw_value)
        if parsed is None:
            continue
        normalized[area] = max(0.0, min(parsed, 100.0))

    return normalized or None


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
    summary: Optional[Dict[str, Any]] = None
    coverage: Optional[Dict[str, Any]] = None
    signals: Optional[Dict[str, Any]] = None
    livePatch: Optional[Dict[str, Any]] = None
    cycleTrace: Optional[Dict[str, Any]] = None
    topicNavigation: Optional[Dict[str, Any]] = None
    stage: str = "discovery"
    mode: bool = False
    lastAssistantQuestion: str = ""
    savedAt: Optional[str] = None
    lang: str = "ar"

    def __init__(self, **data: Any) -> None:  # noqa: ANN401
        if "lang" in data and data["lang"] not in ("ar", "en"):
            data["lang"] = "ar"
        super().__init__(**data)


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
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    await _get_user_project(db, project_id, user)
    
    # We do not lock the project here anymore to prevent blocking the fast chatter.
    # The background task will lock the project when updating SRSDraft.
    try:
        service = get_interview_service()
        stmt_draft = select(SRSDraft).where(SRSDraft.project_id == project_id).order_by(SRSDraft.version.desc()).limit(1)
        latest_draft = await db.scalar(stmt_draft)
        
        draft_content = latest_draft.content if latest_draft and isinstance(latest_draft.content, dict) else {}
        current_summary = draft_content.get("summary", {}) if draft_content else {}
        current_coverage = draft_content.get("coverage", {}) if draft_content else {}

        if not current_summary and payload.last_summary:
            current_summary = _normalize_last_summary(payload.last_summary) or {}
        if not current_coverage and payload.last_coverage:
            current_coverage = _normalize_last_coverage(payload.last_coverage) or {}

        # 1. Run the super fast Chatter Agent
        result = await service.get_chat_response(
            db=db, project_id=project_id,
            language=payload.language,
            last_summary=current_summary,
            last_coverage=current_coverage,
            aim_for_100=payload.aim_for_100
        )

        # 2. Fire the asynchronous Extractor Agent in the background
        # Pass async_session_maker to create a new session isolated from the HTTP request context
        background_tasks.add_task(
            service.extract_background_patches,
            project_id=project_id,
            language=payload.language,
            session_factory=async_session_maker
        )

        # 3. Return immediately!
        return {
            "question": result["question"],
            "stage": result["stage"],
            "done": result["done"],
            "suggested_answers": result.get("suggested_answers"),
            "summary": current_summary, # we just return the current one, background task updates it
            "coverage": current_coverage,
            "signals": result.get("signals"),
            "live_patch": result.get("live_patch"),
            "cycle_trace": result.get("cycle_trace"),
            "topic_navigation": result.get("topic_navigation"),
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Interview error: {e}")
        raise HTTPException(status_code=500, detail="Processing error")


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
    draft_data = payload.model_dump()
    draft_data["summary"] = _normalize_last_summary(payload.summary)
    draft_data["coverage"] = _normalize_last_coverage(payload.coverage)

    metadata = dict(project.extra_metadata or {})
    metadata["interview_draft"] = draft_data
    project.extra_metadata = metadata
    await db.commit()
    return {"success": True, "draft": draft_data}


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
