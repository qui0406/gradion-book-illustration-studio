import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, Depends

from app.models.project import CreateProjectRequest, Project, StatusEnum, StepStateEnum
from app.services import storage_service
from app.services.storage_service import is_valid_email
from app.dependencies import get_current_user_email, get_authenticated_project

router = APIRouter()


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
async def create_project_from_textarea(
    req: CreateProjectRequest,
    current_user_email: str = Depends(get_current_user_email)
):
    """
    Luồng 1: Nhận trực tiếp chuỗi book_text từ giao diện Textarea (JSON payload).
    """
    req_email = req.user_email.strip().lower() if req.user_email else current_user_email
    if req_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot create project for another user")

    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="Project title is required")
    if not req.book_text or not req.book_text.strip():
        raise HTTPException(status_code=400, detail="Book text content is required")

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    new_project = Project(
        id=project_id,
        user_email=current_user_email,
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


@router.post("/upload", response_model=Dict[str, Any])
async def create_project_from_file(
    user_email: str = Form(..., description="User email"),
    title: str = Form(..., description="Project title"),
    file: UploadFile = File(..., description="Book content .txt file"),
    current_user_email: str = Depends(get_current_user_email)
):
    """
    Luồng 2: Upload file .txt nội dung sách (Multipart Form Data).
    Backend đọc file .txt bằng UTF-8 và trích xuất thành book_text.
    """
    req_email = user_email.strip().lower() if user_email else current_user_email
    if req_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot create project for another user")

    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Project title is required")

    # Validate file extension
    filename = file.filename or ""
    if not filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    try:
        content_bytes = await file.read()
        book_text = content_bytes.decode("utf-8").strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file UTF-8 content: {str(e)}")

    if not book_text:
        raise HTTPException(status_code=400, detail="Uploaded .txt file is empty")

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    new_project = Project(
        id=project_id,
        user_email=current_user_email,
        title=title.strip(),
        book_text=book_text,
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
async def list_projects(clean_email: str = Depends(get_current_user_email)):
    """
    Retrieve user profile and all belonging projects wrapped in a data key.
    """
    user_data = storage_service.load_user(clean_email)
    user_name = user_data.get("name", "") if user_data else ""

    projects = storage_service.list_user_projects(clean_email)

    return {
        "email": clean_email,
        "name": user_name,
        "data": [p.model_dump() for p in projects]
    }


@router.get("/{project_id}", response_model=Dict[str, Any])
async def get_project(project: Project = Depends(get_authenticated_project)):
    """
    Retrieve detailed status and state of a specific project. Enforces ownership check.
    """
    return {"data": project}

