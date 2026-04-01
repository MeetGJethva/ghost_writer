"""
Project Registration API — Router for managing project lifecycle.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from the_orchestrator.gateway.database import get_db
from the_orchestrator.gateway.models.db_models import Project

router = APIRouter(prefix="/projects", tags=["projects"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    keywords: str | None = Field(None, description="Keywords for the project")
    folder_path: str = Field(..., description="Absolute path to the project folder")


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    keywords: str | None
    folder_path: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new project",
)
async def register_project(
    body: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> Project:
    # Check if project already exists
    stmt = select(Project).where(Project.name == body.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{body.name}' already exists.",
        )

    project = Project(
        name=body.name,
        description=body.description,
        keywords=body.keywords,
        folder_path=body.folder_path,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get(
    "/",
    response_model=list[ProjectResponse],
    summary="List all registered projects",
)
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> Sequence[Project]:
    stmt = select(Project).order_by(Project.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Project:
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return project