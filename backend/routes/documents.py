"""
Document Routes.
API endpoints for document management.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.database import get_db
from backend.database.models import Project, User
from backend.routes.auth import get_current_user
from backend.controllers.document_controller import DocumentController

router = APIRouter(tags=["Documents"])
_document_controller = None


def get_document_controller() -> DocumentController:
    global _document_controller
    if _document_controller is None:
        _document_controller = DocumentController()
    return _document_controller


async def _verify_project_access(db: AsyncSession, project_id: int, user: User):
    """Verify the user owns this project."""
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user.id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")


# Response Models
class AssetResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: str
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    extra_metadata: Dict[str, Any]

    class Config:
        from_attributes = True


# Routes
@router.post("/projects/{project_id}/documents", response_model=AssetResponse, status_code=201)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload document to project.
    Document will be processed in background.
    """
    await _verify_project_access(db, project_id, user)
    try:
        # Read file
        file_content = await file.read()
        file_size = len(file_content)

        # Upload document
        document_controller = get_document_controller()
        asset = await document_controller.upload_document(
            db=db,
            project_id=project_id,
            file_content=file_content,
            filename=file.filename,
            file_size=file_size
        )

        # Process in background
        background_tasks.add_task(
            document_controller.process_document,
            asset_id=asset.id
        )

        return asset

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/documents", response_model=List[AssetResponse])
async def list_project_documents(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all documents in project."""
    await _verify_project_access(db, project_id, user)
    try:
        document_controller = get_document_controller()
        documents = await document_controller.list_project_documents(
            db=db,
            project_id=project_id
        )
        return documents
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documents/{asset_id}", response_model=AssetResponse)
async def get_document(
    asset_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document by ID."""
    try:
        document_controller = get_document_controller()
        document = await document_controller.get_document(db=db, asset_id=asset_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/documents/{asset_id}/process", response_model=AssetResponse)
async def process_document(
    asset_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger document processing."""
    try:
        document_controller = get_document_controller()
        await document_controller.process_document(asset_id=asset_id)
        document = await document_controller.get_document(db=db, asset_id=asset_id)
        return document
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{asset_id}", status_code=204)
async def delete_document(
    asset_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete document."""
    try:
        document_controller = get_document_controller()
        deleted = await document_controller.delete_document(db=db, asset_id=asset_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
