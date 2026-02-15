from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.judging_service import JudgingService

router = APIRouter(tags=["Judging"])
_judging_service: JudgingService | None = None


def get_judging_service() -> JudgingService:
    """
    Judging Service Routes for FastAPI
    Handles endpoints for judging and refining SRS documents.
    Author: Adel Sobhy
    Date: 2026-02-15
    """
    global _judging_service
    if _judging_service is None:
        _judging_service = JudgingService()
    return _judging_service


class JudgingRequest(BaseModel):
    project_id: int
    srs_content: dict
    analysis_content: str = ""
    language: str = Field(default="ar", pattern="^(ar|en)$")
    store_refined: bool = True


class JudgingResponse(BaseModel):
    technical_critique: dict
    business_critique: dict
    refined_srs: dict
    refined_analysis: str
    summary: dict
    timestamp: str


@router.post("/projects/{project_id}/judge", response_model=JudgingResponse)
async def judge_project(
    project_id: int,
    payload: JudgingRequest,
    db: AsyncSession = Depends(get_db),
):
    service = get_judging_service()

    try:
        result = await service.judge_and_refine(
            srs_content=payload.srs_content,
            analysis_content=payload.analysis_content,
            language=payload.language,
            store_refined=payload.store_refined,
            db=db,
            project_id=project_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Judging failed: {str(e)}")
