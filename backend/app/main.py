import os
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.steps import router as steps_router
from app.services import storage_service

app = FastAPI(
    title="Gradion Book Illustration Studio API",
    description="Backend API for converting book content into character portraits and chapter illustrations via Gemini API",
    version="0.1.0",
)

# Configure CORS
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(steps_router, prefix="/api/projects/{project_id}/steps", tags=["steps"])


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint returning system status.
    """
    return {"status": "ok"}


@app.get("/api/images/{project_id}/{folder}/{entity_id}")
@app.get("/api/images/{project_id}/{entity_id}")
async def serve_project_image(project_id: str, entity_id: str, folder: Optional[str] = None):
    """
    Serve generated PNG images for character portraits and chapter illustrations.
    """
    safe_proj = re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)
    safe_entity = re.sub(r'[^a-zA-Z0-9_-]', '_', entity_id)

    if folder:
        safe_folder = re.sub(r'[^a-zA-Z0-9_-]', '_', folder)
        file_path = os.path.join(storage_service.IMAGES_DIR, safe_proj, safe_folder, f"{safe_entity}.png")
    else:
        file_path = os.path.join(storage_service.IMAGES_DIR, safe_proj, f"{safe_entity}.png")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(file_path, media_type="image/png")
