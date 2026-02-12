"""
Interview routes for guided requirements questions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
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
    summary: Any = None
    coverage: dict | None = None


@router.post("/projects/{project_id}/interview/next", response_model=InterviewResponse)
async def next_question(project_id: int, payload: InterviewRequest, db: AsyncSession = Depends(get_db)):
    service = get_interview_service()
    result = await service.get_next_question(
        db, project_id, payload.language,
        last_summary=payload.last_summary,
        last_coverage=payload.last_coverage,
    )
    return result
