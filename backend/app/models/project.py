from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    STYLE = "style"
    CHARACTERS = "characters"
    PORTRAITS = "portraits"
    CHAPTERS = "chapters"
    ILLUSTRATIONS = "illustrations"


class Character(BaseModel):
    """Skeleton model for adult characters (max 2 enforced)."""

    id: str
    name: str
    description: str
    is_adult: bool = True
    portrait_url: Optional[str] = None


class Chapter(BaseModel):
    """Skeleton model for chapter (max 1 enforced)."""

    id: str
    title: str
    summary: str
    illustration_url: Optional[str] = None


class Project(BaseModel):
    """
    Skeleton Pydantic model representing project state.
    """

    id: str
    title: str
    book_content: str
    current_step: PipelineStep = PipelineStep.STYLE
    step_status: StepStatus = StepStatus.IDLE
    art_style: Optional[str] = None
    characters: List[Character] = Field(default_factory=list, max_length=2)
    chapters: List[Chapter] = Field(default_factory=list, max_length=1)
    error_message: Optional[str] = None
