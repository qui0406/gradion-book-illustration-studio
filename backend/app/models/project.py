from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
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


class CreateProjectRequest(BaseModel):
    user_email: str
    title: str
    book_text: str


class Character(BaseModel):
    id: str
    name: str
    image_prompt: str
    description: Optional[str] = None
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
    created_at: str
    
    # === PIPELINE STATE ===
    status: StatusEnum = StatusEnum.CREATED
    current_step: int = Field(default=1, ge=1, le=5)
    step_state: StepStateEnum = StepStateEnum.IDLE
    step_started_at: Optional[str] = None
    step_error: Optional[str] = None
    
    # === STEP 1 RESULTS ===
    style: Optional[str] = None
    style_source: Optional[str] = None
    style_reasoning: Optional[str] = None
    
    # === STEP 2 RESULTS ===
    characters: List[Character] = []
    
    # === STEP 3 RESULTS ===
    portraits: List[Dict[str, Any]] = []  # [{character_name, image_path, image_data}]
    
    # === STEP 4 RESULTS ===
    chapters: List[Chapter] = []
    
    # === STEP 5 RESULTS ===
    illustrations: List[Dict[str, Any]] = []  # [{chapter_name, image_path}]
    
    # === GEMINI SESSION ===
    gemini_session_ref: Optional[str] = None  # interaction_id
    
    # === VALIDATION ===
    @field_validator("characters")
    @classmethod
    def validate_characters(cls, v: List[Character]) -> List[Character]:
        if len(v) > 2:
            raise ValueError("Maximum 2 adult characters allowed")
        return v
    
    @field_validator("chapters")
    @classmethod
    def validate_chapters(cls, v: List[Chapter]) -> List[Chapter]:
        if len(v) > 1:
            raise ValueError("Maximum 1 chapter allowed")
        return v
