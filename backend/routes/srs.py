"""
SRS draft routes.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.srs_service import SRSService

router = APIRouter(tags=["SRS"])
_srs_service = None


def get_srs_service() -> SRSService:
    global _srs_service
    if _srs_service is None:
        _srs_service = SRSService()
    return _srs_service


class SRSRefreshRequest(BaseModel):
    language: str = Field(default="ar", pattern="^(ar|en)$")


class SRSDraftResponse(BaseModel):
    project_id: int
    version: int
    status: str
    language: str
    content: dict
    created_at: str | None = None


@router.get("/projects/{project_id}/srs", response_model=SRSDraftResponse)
async def get_latest_srs(project_id: int, db: AsyncSession = Depends(get_db)):
    service = get_srs_service()
    draft = await service.get_latest_draft(db, project_id)
    if not draft:
        raise HTTPException(status_code=404, detail="SRS draft not found")

    return {
        "project_id": draft.project_id,
        "version": draft.version,
        "status": draft.status,
        "language": draft.language,
        "content": draft.content,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }


@router.post("/projects/{project_id}/srs/refresh", response_model=SRSDraftResponse)
async def refresh_srs(project_id: int, payload: SRSRefreshRequest, db: AsyncSession = Depends(get_db)):
    service = get_srs_service()
    try:
        draft = await service.generate_draft(db, project_id, payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "project_id": draft.project_id,
        "version": draft.version,
        "status": draft.status,
        "language": draft.language,
        "content": draft.content,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }


@router.get("/projects/{project_id}/srs/export")
async def export_srs(project_id: int, db: AsyncSession = Depends(get_db)):
    service = get_srs_service()
    draft = await service.get_latest_draft(db, project_id)
    if not draft:
        raise HTTPException(status_code=404, detail="SRS draft not found")

    pdf_bytes = service.export_pdf(draft)
    filename = f"srs_project_{project_id}_v{draft.version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
