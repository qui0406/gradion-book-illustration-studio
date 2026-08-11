import json
import os
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


# --- USER STORAGE ---

def get_user_file_path(email: str) -> str:
    safe_email = email.replace("/", "_").replace("\\", "_")
    return os.path.join(USERS_DIR, f"{safe_email}.json")


def save_user(user_data: dict) -> dict:
    file_path = get_user_file_path(user_data["email"])
    lock_path = f"{file_path}.lock"
    with FileLock(lock_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    return user_data


def load_user(email: str) -> Optional[dict]:
    file_path = get_user_file_path(email)
    if not os.path.exists(file_path):
        return None
    lock_path = f"{file_path}.lock"
    with FileLock(lock_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)


# --- PROJECT STORAGE ---

def get_project_file_path(project_id: str) -> str:
    return os.path.join(PROJECTS_DIR, f"{project_id}.json")


def save_project(project: Project) -> Project:
    file_path = get_project_file_path(project.id)
    lock_path = f"{file_path}.lock"
    project_dict = project.model_dump()
    with FileLock(lock_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(project_dict, f, ensure_ascii=False, indent=2)
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
    projects = []
    if not os.path.exists(PROJECTS_DIR):
        return projects

    for filename in os.listdir(PROJECTS_DIR):
        if filename.endswith(".json") and not filename.endswith(".lock"):
            project_id = filename[:-5]
            proj = load_project(project_id)
            if proj and proj.user_email == user_email:
                projects.append(proj)

    projects.sort(key=lambda x: x.created_at, reverse=True)
    return projects
