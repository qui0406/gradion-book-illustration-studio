# Technical Plan — Book Illustration Studio

## 1. Data model

### Project
- id, user_email, title, book_text, created_at
- status: CREATED | STYLE_SET | CHARACTERS_GENERATED | PORTRAITS_GENERATED | CHAPTERS_GENERATED | DONE
- step_state: IDLE | RUNNING | FAILED
- step_started_at: timestamp | null
- step_error: string | null
- style: string | null
- characters: [{id, name, image_prompt, portrait_ready, portrait_path}]  (max 2)
- chapters: [{id, title, illustration_prompt, illustration_ready, illustration_path}]  (max 1)
- gemini_session_ref: string | null   

### User
- email, name, created_at

## 2. Storage layout
data/
  users/{email}.json
  projects/{project_id}.json
  images/{project_id}/{entity_id}.png

## 3. API endpoints 
- POST /api/auth/signin              -> {email, name} -> user
- GET  /api/projects?email=          -> list user projects
- POST /api/projects                 -> create project (title, book_text)
- GET  /api/projects/{id}            -> project details (polling)
- POST /api/projects/{id}/steps/style          -> {style?: string}
- POST /api/projects/{id}/steps/characters
- POST /api/projects/{id}/steps/portraits
- POST /api/projects/{id}/steps/chapters
- POST /api/projects/{id}/steps/illustrations
- POST /api/projects/{id}/steps/retry          -> retry FAILED/stale steps
- GET  /api/images/{project_id}/{entity_id}    -> serve image file

## 4. Concurrency & resume strategy
- Each step: write step_state= RUNNING + step_started_at BEFORE calling Gemini, run in background (non-blocking HTTP response).
- If request arrives while step_state=RUNNING -> return current state, DO NOT call Gemini again.
- If step_state=RUNNING but (now - step_started_at) > STALE_THRESHOLD (based on real Gemini latency, not demo numbers) -> treat as stale, allow /retry.
- Lock file writes per project_id (file lock or in-memory mutex + re-check state on disk).

## 5. Gemini integration (theo notebook-notes.md)
- Summarized mechanism as documented in `notebook-notes.md`.
- Book text sent once during Style step, save session_ref, re-use for subsequent steps.

## 6. Frontend routing
- /auth, /projects, /projects/new, /projects/:id

## 7. Testing strategy
- Backend: unit test state machine (status/step_state transitions), lock behavior, retry logic
- Frontend: test loading/error/empty state của ProjectDetail, EntityCard