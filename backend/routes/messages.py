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
from backend.database.models import ChatMessage

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


@router.get("/projects/{project_id}/messages", response_model=List[MessageOut])
async def get_messages(project_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve all chat messages for a project, ordered by creation time."""
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
async def add_messages(project_id: int, payload: MessagesRequest, db: AsyncSession = Depends(get_db)):
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

    return {"success": True, "count": len(payload.messages)}


@router.delete("/projects/{project_id}/messages")
async def clear_messages(project_id: int, db: AsyncSession = Depends(get_db)):
    """Delete all chat messages for a project."""
    stmt = delete(ChatMessage).where(ChatMessage.project_id == project_id)
    result = await db.execute(stmt)
    deleted = int(result.rowcount or 0)
    return {"success": True, "deleted": deleted}
