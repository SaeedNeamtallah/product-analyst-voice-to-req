"""
Project handoff routes: send SRS + summary to engineering team.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.database.models import SRSDraft, Project, ChatMessage, User
from backend.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Handoff"])


class HandoffRequest(BaseModel):
    client_name: str = Field(default="")
    client_email: str = Field(default="")
    notes: str = Field(default="")


class HandoffResponse(BaseModel):
    success: bool
    message: str
    package: dict


@router.post("/projects/{project_id}/handoff", response_model=HandoffResponse)
async def create_handoff(
    project_id: int,
    data: HandoffRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get project (scoped to user)
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get latest SRS
    srs_result = await db.execute(
        select(SRSDraft)
        .where(SRSDraft.project_id == project_id)
        .order_by(SRSDraft.version.desc())
        .limit(1)
    )
    srs_draft = srs_result.scalar_one_or_none()

    # Get conversation summary
    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = list(msgs_result.scalars().all())

    # Build the handoff package
    conversation_summary = []
    for msg in messages[-20:]:  # Last 20 messages
        conversation_summary.append({
            "role": msg.role,
            "content": msg.content[:500],  # Truncate long messages
        })

    srs_content = srs_draft.content if srs_draft else None

    package = {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description or "",
        },
        "srs": srs_content,
        "conversation_summary": conversation_summary,
        "client": {
            "name": data.client_name,
            "email": data.client_email,
            "notes": data.notes,
        },
        "message_count": len(messages),
    }

    logger.info(f"Handoff package created for project {project_id}")

    return {
        "success": True,
        "message": "Handoff package created successfully",
        "package": package,
    }
