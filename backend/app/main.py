from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.steps import router as steps_router

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
