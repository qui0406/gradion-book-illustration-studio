from datetime import datetime, timezone
from pydantic import BaseModel, Field


class UserSignInRequest(BaseModel):
    email: str
    name: str


class UserResponse(BaseModel):
    email: str
    name: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
