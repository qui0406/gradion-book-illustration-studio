"""
Storage Service Skeleton.

Handles CRUD operations for project state and generated assets using local JSON files on disk (`data/`).
"""


def save_project(project_data: dict) -> bool:
    """
    Skeleton: Write project state dictionary to data/projects/{project_id}.json.
    """
    pass


def load_project(project_id: str) -> dict:
    """
    Skeleton: Read project state dictionary from data/projects/{project_id}.json.
    """
    pass


def list_all_projects() -> list[dict]:
    """
    Skeleton: Return a list of all project metadata saved on disk.
    """
    pass
