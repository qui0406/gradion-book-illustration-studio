import asyncio
from typing import Dict

class StepLockManager:
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
    
    def get_lock(self, project_id: str) -> asyncio.Lock:
        if project_id not in self._locks:
            self._locks[project_id] = asyncio.Lock()
        return self._locks[project_id]

step_lock_manager = StepLockManager()
