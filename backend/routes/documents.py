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
from backend.database.connection import async_session_maker
from backend.database.models import Asset, Project, User
from backend.routes.auth import get_current_user
from backend.config import settings
from backend.services.file_service import FileService

router = APIRouter(tags=["Documents"])
_file_service = FileService()


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


class PresignUploadRequest(BaseModel):
    filename: str
    file_size: int
    content_type: Optional[str] = None


class PresignUploadResponse(BaseModel):
    upload_url: str
    file_key: str
    unique_filename: str
    content_type: str
    expires_in: int


class CompleteUploadRequest(BaseModel):
    unique_filename: str
    original_filename: str
    file_key: str
    file_size: int
    file_type: str


# Routes
@router.post("/projects/{project_id}/documents/presign", response_model=PresignUploadResponse)
async def presign_document_upload(
    project_id: int,
    payload: PresignUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(db, project_id, user)
    if payload.file_size > _file_service.max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB")

    ext = (payload.filename.rsplit('.', 1)[-1].lower() if '.' in payload.filename else "")
    if f".{ext}" not in _file_service.get_supported_extensions():
        raise HTTPException(status_code=400, detail="Unsupported file type. Supported: PDF, TXT, DOCX")

    try:
        response = await _file_service.generate_presigned_upload(
            project_id=project_id,
            filename=payload.filename,
            content_type=payload.content_type or "application/octet-stream",
        )
        return PresignUploadResponse(**response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/projects/{project_id}/documents/complete", response_model=AssetResponse, status_code=201)
async def complete_document_upload(
    project_id: int,
    payload: CompleteUploadRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(db, project_id, user)
    if payload.file_size > _file_service.max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB")

    file_type = str(payload.file_type or "").lower()
    if f".{file_type}" not in _file_service.get_supported_extensions():
        raise HTTPException(status_code=400, detail="Unsupported file type. Supported: PDF, TXT, DOCX")

    if str(settings.object_storage_provider or "local").strip().lower() in {"aws_s3", "s3"}:
        file_path = f"s3://{settings.aws_s3_bucket}/{payload.file_key}"
    else:
        file_path = payload.file_key

    asset = Asset(
        project_id=project_id,
        filename=payload.unique_filename,
        original_filename=payload.original_filename,
        file_path=file_path,
        file_size=payload.file_size,
        file_type=file_type,
        status="uploaded",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    background_tasks.add_task(
        _process_document_asset,
        asset_id=asset.id,
    )
    return asset


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

        is_valid, error_msg = _file_service.validate_file(file.filename, file_size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg or "Invalid file")

        unique_filename, file_path = await _file_service.save_upload_file(
            file_content=file_content,
            filename=file.filename,
            project_id=project_id,
        )
        file_type = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ""
        asset = Asset(
            project_id=project_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            status="uploaded",
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)

        # Process in background
        background_tasks.add_task(
            _process_document_asset,
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
        stmt = select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())
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
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        document = result.scalar_one_or_none()
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
        await _process_document_asset(asset_id=asset_id)
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
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
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="Document not found")

        await _file_service.delete_file(asset.file_path)
        await db.delete(asset)
        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _process_document_asset(asset_id: int) -> bool:
    async with async_session_maker() as db:
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one_or_none()
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        asset.status = "processing"
        await db.commit()

        try:
            text = await _file_service.extract_text(asset.file_path)
            asset.extracted_text = text
            asset.status = "completed"
            asset.processed_at = datetime.utcnow()
            metadata = dict(asset.extra_metadata or {})
            metadata.update({"stage": "completed", "progress": 100, "processed_chunks": 1, "total_chunks": 1})
            asset.extra_metadata = metadata
            await db.commit()
            return True
        except Exception as exc:  # noqa: BLE001
            asset.status = "failed"
            asset.error_message = str(exc)
            await db.commit()
            raise
