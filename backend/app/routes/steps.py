from fastapi import APIRouter

router = APIRouter()


@router.post("/execute")
async def execute_step(project_id: str):
    """
    Skeleton: Trigger execution of current pipeline step for a project.
    Pipeline steps: Style -> Characters -> Portraits -> Chapters -> Illustrations.
    Enforces project locking, no auto-retries, sequential image generation.
    To be implemented with the user in future steps.
    """
    pass


@router.post("/retry")
async def retry_step(project_id: str):
    """
    Skeleton: User-triggered manual retry for a failed or cancelled step.
    To be implemented with the user in future steps.
    """
    pass
