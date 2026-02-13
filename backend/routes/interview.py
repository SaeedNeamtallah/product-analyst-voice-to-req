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
from backend.database.models import Project
from backend.services.interview_service import InterviewService

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


class InterviewDraftPayload(BaseModel):
    summary: Optional[Dict[str, List[str]]] = None
    coverage: Optional[Dict[str, float]] = None
    stage: str = "discovery"
    mode: bool = False
    lastAssistantQuestion: str = ""
    savedAt: Optional[str] = None
    lang: str = Field(default="ar", pattern="^(ar|en)$")


def _get_project_interview_draft(project: Project) -> Optional[Dict[str, Any]]:
    metadata = project.extra_metadata if isinstance(project.extra_metadata, dict) else {}
    draft = metadata.get("interview_draft")
    return draft if isinstance(draft, dict) else None


@router.post("/projects/{project_id}/interview/next", response_model=InterviewResponse)
async def next_question(project_id: int, payload: InterviewRequest, db: AsyncSession = Depends(get_db)):
    service = get_interview_service()
    result = await service.get_next_question(
        db, project_id, payload.language,
        last_summary=payload.last_summary,
        last_coverage=payload.last_coverage,
    )
    return result


@router.get("/projects/{project_id}/interview/draft")
async def get_interview_draft(project_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"draft": _get_project_interview_draft(project)}


@router.post("/projects/{project_id}/interview/draft")
async def save_interview_draft(project_id: int, payload: InterviewDraftPayload, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = dict(project.extra_metadata or {})
    metadata["interview_draft"] = payload.model_dump()
    project.extra_metadata = metadata
    return {"success": True, "draft": metadata["interview_draft"]}


@router.delete("/projects/{project_id}/interview/draft")
async def clear_interview_draft(project_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = dict(project.extra_metadata or {})
    metadata.pop("interview_draft", None)
    project.extra_metadata = metadata
    return {"success": True}
