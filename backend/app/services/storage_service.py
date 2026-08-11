import json
import os
import re
from typing import Dict, List, Optional
from filelock import FileLock
from app.models.project import Project


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
USERS_DIR = os.path.join(DATA_DIR, "users")
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
IMAGES_DIR = os.path.join(DATA_DIR, "images")

# Ensure base data directories exist
os.makedirs(USERS_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# --- USER STORAGE ---

def get_user_file_path(email: str) -> str:
    # Validate email format
    if not is_valid_email(email):
        raise ValueError("Invalid email format")

    # Only allow safe characters
    safe_email = re.sub(r'[^a-zA-Z0-9@._-]', '_', email)

    # Ensure path stays within USERS_DIR (Prevent Path Traversal)
    filepath = os.path.join(USERS_DIR, f"{safe_email}.json")
    real_path = os.path.realpath(filepath)
    base_path = os.path.realpath(USERS_DIR)

    if not real_path.startswith(base_path):
        raise ValueError("Path traversal detected")

    return real_path


def save_user(user_data: dict) -> dict:
    if "project_ids" not in user_data:
        user_data["project_ids"] = []
    file_path = get_user_file_path(user_data["email"])
    lock_path = f"{file_path}.lock"
    with FileLock(lock_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    return user_data


def load_user(email: str) -> Optional[dict]:
    if not is_valid_email(email):
        raise ValueError("Invalid email format")

    file_path = get_user_file_path(email)
    if not os.path.exists(file_path):
        return None
    lock_path = f"{file_path}.lock"
    with FileLock(lock_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "project_ids" not in data:
                data["project_ids"] = []
            return data


def add_project_to_user(user_email: str, project_id: str) -> None:
    user = load_user(user_email)
    if user:
        if project_id not in user.get("project_ids", []):
            user.setdefault("project_ids", []).append(project_id)
            save_user(user)


# --- PROJECT STORAGE ---

def get_project_file_path(project_id: str) -> str:
    # Ensure safe project_id filename
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)
    filepath = os.path.join(PROJECTS_DIR, f"{safe_id}.json")
    real_path = os.path.realpath(filepath)
    base_path = os.path.realpath(PROJECTS_DIR)

    if not real_path.startswith(base_path):
        raise ValueError("Path traversal detected")
    return real_path


def save_project(project: Project) -> Project:
    file_path = get_project_file_path(project.id)
    lock_path = f"{file_path}.lock"
    project_dict = project.model_dump()
    with FileLock(lock_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(project_dict, f, ensure_ascii=False, indent=2)

    # Update user index file
    add_project_to_user(project.user_email, project.id)
    return project


def load_project(project_id: str) -> Optional[Project]:
    file_path = get_project_file_path(project_id)
    if not os.path.exists(file_path):
        return None
    lock_path = f"{file_path}.lock"
    with FileLock(lock_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Project(**data)


def list_user_projects(user_email: str) -> List[Project]:
    projects_dict = {}

    # Scan projects directory for all files belonging to user
    if os.path.exists(PROJECTS_DIR):
        for filename in os.listdir(PROJECTS_DIR):
            if filename.endswith(".json") and not filename.endswith(".lock"):
                project_id = filename[:-5]
                proj = load_project(project_id)
                if proj and proj.user_email == user_email:
                    projects_dict[proj.id] = proj

    projects = list(projects_dict.values())
    projects.sort(key=lambda x: x.created_at, reverse=True)

    # Sync project_ids to user profile if needed
    user = load_user(user_email)
    if user:
        current_ids = [p.id for p in projects]
        if set(user.get("project_ids", [])) != set(current_ids):
            user["project_ids"] = current_ids
            save_user(user)

    return projects
