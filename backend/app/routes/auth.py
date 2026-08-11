import re
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from app.models.user import UserSignInRequest, UserResponse
from app.services import storage_service
from app.services.storage_service import is_valid_email

router = APIRouter()


@router.post("/signin", response_model=UserResponse)
async def signin(req: UserSignInRequest):
    """
    Sign in / Register user by Email & Name.
    Saves user info to data/users/{email}.json via storage_service.
    """
    if not req.email or not req.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    email = req.email.strip().lower()

    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    name = req.name.strip()

    # Validate name length
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")

    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Name must not exceed 100 characters")

    # Validate name characters (supports English & Vietnamese Unicode accents, spaces, hyphens, dots)
    if not re.match(r'^[a-zA-Z\u00C0-\u024F\u1EA0-\u1EFF\s\-\.\']+$', name):
        raise HTTPException(status_code=400, detail="Name contains invalid characters")

    existing_user = storage_service.load_user(email)
    if existing_user:
        return UserResponse(**existing_user)

    user_data = {
        "email": email,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    saved_user = storage_service.save_user(user_data)
    return UserResponse(**saved_user)


@router.get("/me", response_model=UserResponse)
async def get_current_user(email: str = Query(..., description="User email")):
    """
    Retrieve user profile by email query param.
    """
    if not is_valid_email(email.strip().lower()):
        raise HTTPException(status_code=400, detail="Invalid email format")

    user_data = storage_service.load_user(email.strip().lower())
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user_data)
