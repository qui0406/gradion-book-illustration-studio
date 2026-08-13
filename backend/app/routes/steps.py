import asyncio
from fastapi import Depends
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.project import Project, StatusEnum, StepStateEnum
from app.services import storage_service
from app.dependencies import get_authenticated_project

router = APIRouter()

logger = logging.getLogger(__name__)

from app.services.gemini_service import GeminiService
from app.utils.locks import step_lock_manager

def get_gemini_service():
    return GeminiService()


class StyleStepRequest(BaseModel):
    style: Optional[str] = None


STEP_TIMEOUT_SECONDS = {
    1: 60,   # Style: text only, 3-5s normally
    2: 60,   # Characters: text only, 3-5s normally
    3: 180,  # Portraits: 2 images × 30s = 60s, buffer 3x
    4: 60,   # Chapters: text only, 3-5s normally
    5: 120,  # Illustrations: 1 image × 30s = 30s, buffer 4x
}

STATUS_ORDER = [
    StatusEnum.CREATED,
    StatusEnum.STYLE_SET,
    StatusEnum.CHARACTERS_GENERATED,
    StatusEnum.PORTRAITS_GENERATED,
    StatusEnum.CHAPTERS_GENERATED,
    StatusEnum.DONE,
]


class StaleStepError(Exception):
    """Raised when a step is stuck in RUNNING past the timeout threshold.
    The caller (route handler) MUST catch this and explicitly reset
    step_state=IDLE before allowing a retry — it must never be swallowed
    silently, or the on-disk state stays stuck at RUNNING forever."""
    pass

def validate_step_execution_lock(project: Project, step: int, required_min_status: Optional[StatusEnum] = None) -> None:
    """
    1. Validate project is not completed.
    2. Validate precondition: step N cannot run before step N-1 is completed.
    3. Check duplicate-call lock:
       - RUNNING and not yet expired -> raise 409 (block duplicate call).
       - RUNNING but stale -> raise StaleStepError.
    """
    
    # === 0. CHECK PROJECT NOT DONE ===
    if project.status == StatusEnum.DONE:
        raise HTTPException(
            status_code=400,
            detail="Project is already completed"
        )
    
    # === 1. PRECONDITION CHECK ===
    if required_min_status:
        current_idx = STATUS_ORDER.index(project.status)
        required_idx = STATUS_ORDER.index(required_min_status)
        
        if current_idx < required_idx:
            raise HTTPException(
                status_code=400,
                detail=f"Precondition failed: complete '{required_min_status.value}' first."
            )
    
    # === 2. CONCURRENCY LOCK CHECK ===
    if project.step_state != StepStateEnum.RUNNING:
        return  # nothing running, safe to proceed
    
    # If RUNNING but missing timestamp -> abnormal data
    if not project.step_started_at:
        logger.warning(
            f"Project {project.id}: step_state=RUNNING but step_started_at is missing"
        )
        raise StaleStepError("step_state=RUNNING but step_started_at is missing")
    
    # Parse timestamp
    try:
        started_dt = datetime.fromisoformat(project.step_started_at)
    except ValueError as e:
        logger.warning(f"Project {project.id}: invalid step_started_at: {e}")
        raise StaleStepError("step_started_at has invalid format") from e
    
    # Calculate elapsed time
    elapsed_sec = (datetime.now(timezone.utc) - started_dt).total_seconds()
    
    # Get timeout for this specific step
    timeout = STEP_TIMEOUT_SECONDS.get(step, 60)  # default 60s
    
    if elapsed_sec < timeout:
        # Still within timeout -> block duplicate
        raise HTTPException(
            status_code=409,
            detail=f"Step is currently executing. Duplicate request blocked. (Running for {int(elapsed_sec)}s)"
        )
    
    # Expired -> raise StaleStepError so caller can reset
    raise StaleStepError(
        f"Step {step} is stale after {int(elapsed_sec)}s (timeout: {timeout}s)"
    )


# === HELPER: HANDLE STALE STEP ===
def handle_stale_step_exception(project: Project, e: StaleStepError) -> None:
    """
    Reset stale step state to IDLE and save to disk.
    Must be called from route handler when StaleStepError is caught.
    """
    logger.warning(
        f"Resetting stale step for project {project.id}: {e}"
    )
    
    # Reset state
    project.step_state = StepStateEnum.IDLE
    project.step_started_at = None
    project.step_error = f"Stale execution auto-reset: {str(e)}"
    
    # Save to disk
    storage_service.save_project(project)
    
    # Return HTTP response
    raise HTTPException(
        status_code=400,
        detail=f"Previous execution was stale and has been reset. Please try again. Details: {str(e)}"
    )


# === HELPER: MARK STEP RUNNING ===
def mark_step_running(project: Project) -> None:
    """Set step_state to RUNNING and update timestamp."""
    project.step_state = StepStateEnum.RUNNING
    project.step_started_at = datetime.now(timezone.utc).isoformat()
    project.step_error = None
    storage_service.save_project(project)


# === HELPER: MARK STEP COMPLETE ===
def mark_step_complete(project: Project, step: int, new_status: StatusEnum) -> None:
    """Mark step as completed and advance project state."""
    project.step_state = StepStateEnum.IDLE
    project.step_started_at = None
    project.step_error = None
    project.status = new_status
    storage_service.save_project(project)


# === HELPER: MARK STEP FAILED ===
def mark_step_failed(project: Project, error: str) -> None:
    """Mark step as FAILED with error message."""
    project.step_state = StepStateEnum.FAILED
    project.step_started_at = None
    project.step_error = str(error)
    storage_service.save_project(project)


@router.post("/style", response_model=Dict[str, Any])
async def execute_style_step(project_id: str, req: Optional[StyleStepRequest] = None, 
                                gemini_service: GeminiService = Depends(get_gemini_service),
                                _project: Project = Depends(get_authenticated_project)):
    async with step_lock_manager.get_lock(project_id):

        # === 1. LOAD PROJECT ===
        project = storage_service.load_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # === 2. VALIDATE STEP ===
        if project.current_step != 1:
            raise HTTPException(
                status_code=400,
                detail=f"Step 1 is not the current step (current: {project.current_step})"
            )
        
        if project.status == StatusEnum.DONE:
            raise HTTPException(
                status_code=400,
                detail="Project is already completed"
            )
        
        # === 3. VALIDATE EXECUTION LOCK ===
        try:
            validate_step_execution_lock(project, step=1, required_min_status=None)
        except StaleStepError as e:
            handle_stale_step_exception(project, e)

        # === 4. GET USER INPUT ===
        custom_style = req.style if req and req.style else None

        # === 5. MARK AS RUNNING ===
        mark_step_running(project)

        # === 6. EXECUTE ===
        try:
            selected_style, source, session_ref = await asyncio.to_thread(
                gemini_service.extract_art_style,
                project.book_text, custom_style, project.id
            )

            if not selected_style or not selected_style.strip():
                raise ValueError("Extracted art style is empty or invalid")

            # === 7. SAVE RESULTS ===
            project.style = selected_style
            project.style_source = source
            project.gemini_session_ref = session_ref
            
            mark_step_complete(project, step=1, new_status=StatusEnum.STYLE_SET)
            return {"data": project}

        except Exception as e:
            # === 8. ERROR HANDLING ===
            mark_step_failed(project, str(e))
            logger.error(f"Step 1 failed: {e}")
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "too_many_requests" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail=f"Gemini API rate limit exceeded. Please wait and try again. Details: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=f"Step 1 (Style) failed: {error_msg}")


@router.post("/characters", response_model=Dict[str, Any])
async def execute_characters_step(
    project_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service),
    _project: Project = Depends(get_authenticated_project)
):
    """
    Step 2: Extract main adult characters (max 2).
    """
    async with step_lock_manager.get_lock(project_id):
        # === 1. LOAD PROJECT ===
        project = storage_service.load_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # === 2. VALIDATE STEP ===
        if project.current_step != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Step 2 is not the current step (current: {project.current_step})"
            )
        
        if project.status == StatusEnum.DONE:
            raise HTTPException(status_code=400, detail="Project is already completed")
        
        # === 3. VALIDATE PREREQUISITES ===
        if not project.style:
            raise HTTPException(status_code=400, detail="Style must be set first (Step 1)")
        
        if not project.gemini_session_ref:
            raise HTTPException(
                status_code=400, 
                detail="Gemini session not found. Please re-run Step 1."
            )
        
        # === 4. VALIDATE EXECUTION LOCK ===
        try:
            validate_step_execution_lock(project, step=2, required_min_status=StatusEnum.STYLE_SET)
        except StaleStepError as e:
            handle_stale_step_exception(project, e)
        
        # === 5. MARK AS RUNNING ===
        mark_step_running(project)
        
        # === 6. EXECUTE ===
        try:
            characters = await asyncio.to_thread(
                gemini_service.extract_characters,
                session_ref=project.gemini_session_ref,
                style=project.style
            )
            
            # Server-side enforcement: max 2 characters
            if len(characters) > 2:
                characters = characters[:2]
                logger.warning(f"Extracted {len(characters)} characters, truncated to 2")
            
            # === 7. SAVE RESULTS ===
            project.characters = characters
            
            mark_step_complete(project, step=2, new_status=StatusEnum.CHARACTERS_GENERATED)
            logger.info(f"Step 2 completed for project {project_id}: {len(characters)} characters extracted")
            return {"data": project}
        
        except Exception as e:
            # === 8. ERROR HANDLING ===
            mark_step_failed(project, str(e))
            logger.error(f"Step 2 failed: {e}")
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "too_many_requests" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail=f"Gemini API rate limit exceeded. Please wait and try again. Details: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=f"Step 2 (Characters) failed: {error_msg}")


@router.post("/portraits", response_model=Dict[str, Any])
async def execute_portraits_step(
    project_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service),
    _project: Project = Depends(get_authenticated_project)
):
    """
    Step 3: Generate character portraits sequentially.
    """
    async with step_lock_manager.get_lock(project_id):
        # === 1. LOAD PROJECT ===
        project = storage_service.load_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # === 2. VALIDATE STEP ===
        if project.current_step != 3:
            raise HTTPException(
                status_code=400,
                detail=f"Step 3 is not the current step (current: {project.current_step})"
            )
        
        if project.status == StatusEnum.DONE:
            raise HTTPException(status_code=400, detail="Project is already completed")
        
        # === 3. VALIDATE PREREQUISITES ===
        if not project.characters or len(project.characters) == 0:
            raise HTTPException(
                status_code=400, 
                detail="No characters found. Please run Step 2 first."
            )
        
        if not project.style:
            raise HTTPException(status_code=400, detail="Style not found. Please run Step 1 first.")
        
        if not project.gemini_session_ref:
            raise HTTPException(
                status_code=400, 
                detail="Gemini session not found. Please re-run Step 1."
            )
        
        # === 4. VALIDATE EXECUTION LOCK ===
        try:
            validate_step_execution_lock(project, step=3, required_min_status=StatusEnum.CHARACTERS_GENERATED)
        except StaleStepError as e:
            handle_stale_step_exception(project, e)
        
        # === 5. MARK AS RUNNING ===
        mark_step_running(project)
        logger.info(f"Step 3 started for project {project_id}")
        
        # === 6. EXECUTE ===
        try:
            def on_portrait_saved(portrait_item: dict):
                existing_idx = next(
                    (i for i, p in enumerate(project.portraits) if p.get("character_id") == portrait_item.get("character_id")),
                    None
                )
                if existing_idx is not None:
                    project.portraits[existing_idx] = portrait_item
                else:
                    project.portraits.append(portrait_item)

                storage_service.save_project(project)
                logger.info(f"Persisted progress for portrait: {portrait_item.get('character_name')}")

            portraits = await asyncio.to_thread(
                gemini_service.generate_portraits,
                project_id=project_id,
                characters=project.characters,
                style=project.style,
                session_ref=project.gemini_session_ref,
                existing_portraits=project.portraits,
                on_portrait_saved=on_portrait_saved
            )
            
            # === 7. SAVE RESULTS ===
            project.portraits = portraits
            
            mark_step_complete(project, step=3, new_status=StatusEnum.PORTRAITS_GENERATED)
            logger.info(f"Step 3 completed: {len(portraits)} portraits generated")
            return {"data": project}
        
        except Exception as e:
            # === 8. ERROR HANDLING ===
            mark_step_failed(project, str(e))
            logger.error(f"Step 3 failed: {e}")
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "too_many_requests" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail=f"Gemini API rate limit exceeded. Please wait and try again. Details: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=f"Step 3 (Portraits) failed: {error_msg}")


@router.post("/chapters", response_model=Dict[str, Any])
async def execute_chapters_step(
    project_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service),
    _project: Project = Depends(get_authenticated_project)
):
    """
    Step 4: Extract the most visually interesting chapter (max 1) using Gemini.
    """
    async with step_lock_manager.get_lock(project_id):
        # === 1. LOAD PROJECT ===
        project = storage_service.load_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # === 2. VALIDATE STEP ===
        if project.current_step != 4:
            raise HTTPException(
                status_code=400,
                detail=f"Step 4 is not the current step (current: {project.current_step})"
            )

        if project.status == StatusEnum.DONE:
            raise HTTPException(status_code=400, detail="Project is already completed")

        # === 3. VALIDATE PREREQUISITES ===
        if not project.characters or len(project.characters) == 0:
            raise HTTPException(status_code=400, detail="No characters found. Please run Step 2 first.")

        if not project.portraits or len(project.portraits) == 0:
            raise HTTPException(status_code=400, detail="No portraits found. Please run Step 3 first.")

        if not project.style:
            raise HTTPException(status_code=400, detail="Style not found. Please run Step 1 first.")

        if not project.gemini_session_ref:
            raise HTTPException(status_code=400, detail="Gemini session not found. Please re-run Step 1.")

        # === 4. VALIDATE EXECUTION LOCK ===
        try:
            validate_step_execution_lock(project, step=4, required_min_status=StatusEnum.PORTRAITS_GENERATED)
        except StaleStepError as e:
            handle_stale_step_exception(project, e)

        # === 5. MARK AS RUNNING ===
        mark_step_running(project)
        logger.info(f"Step 4 started for project {project_id}")

        # === 6. EXECUTE ===
        try:
            chapters = await asyncio.to_thread(
                gemini_service.extract_chapters,
                session_ref=project.gemini_session_ref,
                characters=project.characters,
                style=project.style,
                max_chapters=1
            )

            # Server-side enforcement: max 1 chapter
            if len(chapters) > 1:
                chapters = chapters[:1]
                logger.warning(f"Truncated chapters to 1")

            if len(chapters) == 0:
                raise RuntimeError("Gemini failed to extract any chapters.")

            # === 7. SAVE RESULTS ===
            project.chapters = chapters

            mark_step_complete(project, step=4, new_status=StatusEnum.CHAPTERS_GENERATED)
            logger.info(f"Step 4 completed: {len(chapters)} chapters extracted")
            return {"data": project}

        except Exception as e:
            # === 8. ERROR HANDLING ===
            mark_step_failed(project, str(e))
            logger.error(f"Step 4 failed: {e}")
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "too_many_requests" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail=f"Gemini API rate limit exceeded. Please wait and try again. Details: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=f"Step 4 (Chapters) failed: {error_msg}")


@router.post("/illustrations", response_model=Dict[str, Any])
async def execute_illustrations_step(
    project_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service),
    _project: Project = Depends(get_authenticated_project)
):
    """
    Step 5: Generate chapter illustrations using Gemini Imagen.
    """
    async with step_lock_manager.get_lock(project_id):
        # === 1. LOAD PROJECT ===
        project = storage_service.load_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # === 2. VALIDATE STEP ===
        if project.current_step != 5:
            raise HTTPException(
                status_code=400,
                detail=f"Step 5 is not the current step (current: {project.current_step})"
            )

        if project.status == StatusEnum.DONE:
            raise HTTPException(status_code=400, detail="Project is already completed")

        # === 3. VALIDATE PREREQUISITES ===
        if not project.chapters or len(project.chapters) == 0:
            raise HTTPException(status_code=400, detail="No chapters found. Please run Step 4 first.")

        if not project.portraits or len(project.portraits) == 0:
            raise HTTPException(status_code=400, detail="No portraits found. Please run Step 3 first.")

        if not project.style:
            raise HTTPException(status_code=400, detail="Style not found. Please run Step 1 first.")

        if not project.gemini_session_ref:
            raise HTTPException(status_code=400, detail="Gemini session not found. Please re-run Step 1.")

        # === 4. VALIDATE EXECUTION LOCK ===
        try:
            validate_step_execution_lock(project, step=5, required_min_status=StatusEnum.CHAPTERS_GENERATED)
        except StaleStepError as e:
            handle_stale_step_exception(project, e)

        # === 5. MARK AS RUNNING ===
        mark_step_running(project)
        logger.info(f"Step 5 started for project {project_id}")

        # === 6. EXECUTE ===
        try:
            def on_illustration_saved(illustration_item: dict):
                existing_idx = next(
                    (i for i, item in enumerate(project.illustrations) if item.get("chapter_id") == illustration_item.get("chapter_id")),
                    None
                )
                if existing_idx is not None:
                    project.illustrations[existing_idx] = illustration_item
                else:
                    project.illustrations.append(illustration_item)

                storage_service.save_project(project)
                logger.info(f"Persisted progress for illustration: {illustration_item.get('chapter_title')}")

            illustrations = await asyncio.to_thread(
                gemini_service.generate_illustrations,
                project_id=project_id,
                chapters=project.chapters,
                portraits=project.portraits,
                style=project.style,
                session_ref=project.gemini_session_ref,
                existing_illustrations=project.illustrations,
                on_illustration_saved=on_illustration_saved
            )

            # Server-side enforcement: 1 illustration per chapter
            if len(illustrations) != len(project.chapters):
                raise RuntimeError(
                    f"Illustration count mismatch: expected {len(project.chapters)}, got {len(illustrations)}"
                )

            # === 7. SAVE RESULTS ===
            project.illustrations = illustrations

            mark_step_complete(project, step=5, new_status=StatusEnum.DONE)
            logger.info(f"Project {project_id} completed! {len(illustrations)} illustrations generated")
            return {"data": project}

        except Exception as e:
            # === 8. ERROR HANDLING ===
            mark_step_failed(project, str(e))
            logger.error(f"Step 5 failed: {e}")
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "too_many_requests" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail=f"Gemini API rate limit exceeded. Please wait and try again. Details: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=f"Step 5 (Illustrations) failed: {error_msg}")


