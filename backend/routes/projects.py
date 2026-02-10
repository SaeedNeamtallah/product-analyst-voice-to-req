"""
Project Routes.
API endpoints for project management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.database import get_db
from backend.controllers.project_controller import ProjectController

router = APIRouter(prefix="/projects", tags=["Projects"])
_project_controller = None


def get_project_controller() -> ProjectController:
    global _project_controller
    if _project_controller is None:
        _project_controller = ProjectController()
    return _project_controller


# Request/Response Models
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    extra_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProjectStatsResponse(BaseModel):
    project: ProjectResponse
    stats: Dict[str, Any]


# Routes
@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    try:
        project_controller = get_project_controller()
        project = await project_controller.create_project(
            db=db,
            name=project_data.name,
            description=project_data.description,
            metadata=project_data.metadata
        )
        return project
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all projects."""
    try:
        project_controller = get_project_controller()
        projects = await project_controller.list_projects(db=db, skip=skip, limit=limit)
        return projects
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get project by ID."""
    try:
        project_controller = get_project_controller()
        project = await project_controller.get_project(db=db, project_id=project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get project statistics."""
    try:
        project_controller = get_project_controller()
        project = await project_controller.get_project(db=db, project_id=project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        stats = await project_controller.get_project_stats(db=db, project_id=project_id)
        
        return {
            "project": project,
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update project."""
    try:
        project_controller = get_project_controller()
        project = await project_controller.update_project(
            db=db,
            project_id=project_id,
            name=project_data.name,
            description=project_data.description,
            metadata=project_data.metadata
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete project and all associated data."""
    try:
        project_controller = get_project_controller()
        deleted = await project_controller.delete_project(db=db, project_id=project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
