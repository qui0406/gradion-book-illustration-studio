from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    """
    Skeleton: Authenticate user / handle session initiation.
    To be implemented with the user in future steps.
    """
    pass


@router.get("/me")
async def get_current_user():
    """
    Skeleton: Retrieve current authenticated user profile.
    To be implemented with the user in future steps.
    """
    pass
