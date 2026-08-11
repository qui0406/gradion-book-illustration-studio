from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class StatusEnum(str, Enum):
    CREATED = "CREATED"
    STYLE_SET = "STYLE_SET"
    CHARACTERS_GENERATED = "CHARACTERS_GENERATED"
    PORTRAITS_GENERATED = "PORTRAITS_GENERATED"
    CHAPTERS_GENERATED = "CHAPTERS_GENERATED"
    DONE = "DONE"


class StepStateEnum(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FAILED = "FAILED"


class Character(BaseModel):
    id: str
    name: str
    image_prompt: str
    portrait_ready: bool = False
    portrait_path: Optional[str] = None


class Chapter(BaseModel):
    id: str
    title: str
    illustration_prompt: str
    illustration_ready: bool = False
    illustration_path: Optional[str] = None


class Project(BaseModel):
    id: str
    user_email: str
    title: str
    book_text: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: StatusEnum = StatusEnum.CREATED
    step_state: StepStateEnum = StepStateEnum.IDLE
    step_started_at: Optional[str] = None
    step_error: Optional[str] = None
    style: Optional[str] = None
    characters: List[Character] = Field(default_factory=list)
    chapters: List[Chapter] = Field(default_factory=list)
    gemini_session_ref: Optional[str] = None

    @field_validator("characters")
    @classmethod
    def validate_max_characters(cls, v: List[Character]) -> List[Character]:
        if len(v) > 2:
            raise ValueError("Maximum 2 adult characters allowed per project")
        return v

    @field_validator("chapters")
    @classmethod
    def validate_max_chapters(cls, v: List[Chapter]) -> List[Chapter]:
        if len(v) > 1:
            raise ValueError("Maximum 1 chapter allowed per project")
        return v
