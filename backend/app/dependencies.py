from typing import Optional
from fastapi import Header, Query, HTTPException, Depends
from app.models.project import Project
from app.services import storage_service
from app.services.storage_service import is_valid_email


async def get_current_user_email(
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    email: Optional[str] = Query(None, alias="email")
) -> str:
    """
    Extract and validate authenticated user email from HTTP headers or query parameters.
    Returns clean user email or raises 401 Unauthorized / 400 Bad Request.
    """
    raw_email = x_user_email or email
    if not raw_email or not raw_email.strip():
        raise HTTPException(
            status_code=401,
            detail="Authentication required: User identity (X-User-Email header or email query param) is missing"
        )
    
    clean_email = raw_email.strip().lower()
    if not is_valid_email(clean_email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    user = storage_service.load_user(clean_email)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed: User account not found. Please sign in."
        )
    
    return clean_email


async def get_authenticated_project(
    project_id: str,
    current_user_email: str = Depends(get_current_user_email)
) -> Project:
    """
    Retrieve project by ID and enforce user ownership.
    Raises 404 if project does not exist, or 403 Forbidden if user is not the project owner.
    """
    project = storage_service.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_email != current_user_email:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You do not own this project"
        )
    
    return project
