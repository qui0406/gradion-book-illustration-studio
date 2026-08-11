"""
Lock Service Skeleton.

Manages concurrency lock per `projectId` to ensure only one pipeline step runs at a time.
"""


def acquire_lock(project_id: str) -> bool:
    """
    Skeleton: Acquire execution lock for a given project. Return True if acquired, False if locked.
    """
    pass


def release_lock(project_id: str) -> None:
    """
    Skeleton: Release execution lock for a given project.
    """
    pass


def is_locked(project_id: str) -> bool:
    """
    Skeleton: Check whether a project execution lock is currently held.
    """
    pass
