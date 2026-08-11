from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_projects():
    """
    Skeleton: Retrieve list of all illustration projects.
    To be implemented with the user in future steps.
    """
    pass


@router.post("/")
async def create_project():
    """
    Skeleton: Create a new project and upload/store book content.
    Must enforce backend validations (e.g. max 2 adult characters, max 1 chapter).
    To be implemented with the user in future steps.
    """
    pass


@router.get("/{project_id}")
async def get_project(project_id: str):
    """
    Skeleton: Get detailed status and payload of a specific project.
    To be implemented with the user in future steps.
    """
    pass
