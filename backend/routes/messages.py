"""
Project chat message routes.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.database.models import ChatMessage, Project, User
from backend.routes.auth import get_current_user
from backend.services.live_patch_service import LivePatchService
from backend.services.telemetry_service import TelemetryService

router = APIRouter(tags=["Messages"])


class MessagePayload(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] | None = None


class MessagesRequest(BaseModel):
    messages: List[MessagePayload]


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


class LivePatchRequest(BaseModel):
    language: str = Field(default="ar", pattern="^(ar|en)$")
    last_summary: Dict[str, List[str]] | None = None
    last_coverage: Dict[str, float] | None = None


async def _get_user_project(db: AsyncSession, project_id: int, user: User) -> Project:
    """Fetch project scoped to the authenticated user. Raises 404 if not found."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user.id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/messages", response_model=List[MessageOut])
async def get_messages(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all chat messages for a project, ordered by creation time."""
    await _get_user_project(db, project_id, user)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        MessageOut(
            id=r.id,
            role=r.role,
            content=r.content,
            metadata=r.extra_metadata,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


@router.post("/projects/{project_id}/messages")
async def add_messages(
    project_id: int,
    payload: MessagesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_project(db, project_id, user)
    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    for msg in payload.messages:
        record = ChatMessage(
            project_id=project_id,
            role=msg.role,
            content=msg.content,
            extra_metadata=msg.metadata or {},
        )
        db.add(record)
        await TelemetryService.record_message_event(
            db=db,
            project_id=project_id,
            metadata_payload=msg.metadata,
        )

    await db.commit()
    return {"success": True, "count": len(payload.messages)}


@router.delete("/projects/{project_id}/messages")
async def clear_messages(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all chat messages for a project."""
    await _get_user_project(db, project_id, user)
    stmt = delete(ChatMessage).where(ChatMessage.project_id == project_id)
    result = await db.execute(stmt)
    deleted = int(result.rowcount or 0)
    await db.commit()
    return {"success": True, "deleted": deleted}


@router.post("/projects/{project_id}/messages/live-patch")
async def refresh_live_patch(
    project_id: int,
    payload: LivePatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build and return live SRS patch from full chat history (not interview-only)."""
    project = await _get_user_project(db, project_id, user)

    messages_stmt = (
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages_result = await db.execute(messages_stmt)
    messages = list(messages_result.scalars().all())

    metadata = project.extra_metadata if isinstance(project.extra_metadata, dict) else {}
    stored_state = metadata.get("live_patch_state") if isinstance(metadata.get("live_patch_state"), dict) else {}

    last_summary = payload.last_summary
    if not isinstance(last_summary, dict):
        last_summary = stored_state.get("summary") if isinstance(stored_state.get("summary"), dict) else {}

    last_coverage = payload.last_coverage
    if not isinstance(last_coverage, dict):
        last_coverage = stored_state.get("coverage") if isinstance(stored_state.get("coverage"), dict) else {}

    result = LivePatchService.build_from_messages(
        language=payload.language,
        messages=messages,
        last_summary=last_summary,
        last_coverage=last_coverage,
    )

    next_metadata = dict(metadata)
    next_metadata["live_patch_state"] = {
        "summary": result.get("summary") or {},
        "coverage": result.get("coverage") or {},
    }
    project.extra_metadata = next_metadata
    await db.commit()

    return result


@router.get("/projects/{project_id}/messages/telemetry")
async def get_messages_telemetry(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_project(db, project_id, user)
    report = await TelemetryService.get_report(db=db, project_id=project_id)
    return report
