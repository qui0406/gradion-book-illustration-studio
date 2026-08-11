import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.project import CreateProjectRequest, Project, StatusEnum, StepStateEnum
from app.services import storage_service

router = APIRouter()


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
async def create_project(req: CreateProjectRequest):
    """
    Create a new illustration project from book text content.
    - Generates unique project_id (proj_...)
    - Initializes status = CREATED, step_state = IDLE
    - Persists JSON state to data/projects/{project_id}.json
    """
    if not req.user_email or not req.user_email.strip():
        raise HTTPException(status_code=400, detail="User email is required")
    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="Project title is required")
    if not req.book_text or not req.book_text.strip():
        raise HTTPException(status_code=400, detail="Book text content is required")

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    new_project = Project(
        id=project_id,
        user_email=req.user_email.strip().lower(),
        title=req.title.strip(),
        book_text=req.book_text.strip(),
        created_at=datetime.now(timezone.utc).isoformat(),
        status=StatusEnum.CREATED,
        step_state=StepStateEnum.IDLE,
        step_started_at=None,
        step_error=None,
        style=None,
        characters=[],
        chapters=[],
        gemini_session_ref=None,
    )

    saved_project = storage_service.save_project(new_project)
    return {"data": saved_project}


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
async def list_projects(email: str = Query(..., description="User email")):
    """
    Retrieve user profile and all belonging projects wrapped in a data key.
    """
    if not email or not email.strip():
        raise HTTPException(status_code=400, detail="User email is required")

    clean_email = email.strip().lower()
    user_data = storage_service.load_user(clean_email)
    user_name = user_data.get("name", "") if user_data else ""

    projects = storage_service.list_user_projects(clean_email)

    return {
        "email": clean_email,
        "name": user_name,
        "data": [p.model_dump() for p in projects]
    }


@router.get("/{project_id}", response_model=Dict[str, Any])
async def get_project(project_id: str):
    """
    Retrieve detailed status and state of a specific project.
    """
    project = storage_service.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"data": project}
