# Architectural & Design Decisions (`DECISIONS.md`)

## AI Copilot Workflow

I built this project using Cursor with Claude 3.5 Sonnet. Each decision below originated from genuine technical discussions — sometimes proposed by me, sometimes by the AI, and always rigorously challenged before reaching the final trade-off.

---

## 1. Separating `status` and `step_state` (AI Proposal Rejected #1)

- **Context & AI Proposal**: Claude proposed a single `status` enum to track progress (e.g., `DRAFT` → `PROCESSING_STEP_2` → `COMPLETED`).
- **My Challenge / Rejection**: I rejected this — a single enum cannot represent "Step 2 is completed, but Step 3 is currently running or failed", which is exactly what a page reload needs to read correctly.
- **Final Decision**: Split state into two independent fields:
  - `status`: Milestone completed (`CREATED | STYLE_SET | CHARACTERS_GENERATED | PORTRAITS_GENERATED | CHAPTERS_GENERATED | DONE`).
  - `step_state`: Current execution state (`IDLE | RUNNING | FAILED`).
- **Trade-off**: Maintaining sync between two fields and handling stuck state timeouts.

---

## 2. Using JSON Files Instead of a Database (AI Challenge Accepted #1)

- **My Proposal**: I wanted to use local JSON files on disk (`data/projects/{id}.json`) to keep the system simple and avoid database setup overhead.
- **AI Counter-argument**: Claude challenged me on concurrent write risks — if a user opens two tabs and clicks "Generate", JSON files could be corrupted.
- **Final Decision**: I accepted the AI's valid challenge and added inter-process file locking via Python's `filelock` library.
- **Trade-off**: Lack of ACID transactions, but guarantees 100% data safety without DB complexity.

---

## 3. Envelope API Response Format with User Context (AI Proposal Rejected #2)

- **Context & AI Proposal**: Claude initially proposed returning a flat JSON array for `GET /api/projects?email=`, where every project item duplicated `"user_email": "user@example.com"`.
- **My Challenge / Rejection**: I rejected returning a flat array — repeating `user_email` on every single project in the array creates unnecessary data duplication and denormalization. Furthermore, a flat array lacks top-level owner context (e.g., user name and email).
- **Final Decision**: Restructured the response into an **Envelope Wrapper format**:
  - Top-level keys contain owner info (`email`, `name`).
  - An inner `"data": [...]` array contains the list of user projects.
- **Trade-off**: Adds one level of nesting (`response.data`), requiring the frontend to unwrap `data`, but eliminates redundant `user_email` fields across array items and provides clean, normalized user context.

---

## 4. Input Validation & Path Traversal Prevention on File-based Storage (User Caught AI Mistake #1)

- **Context & AI Code**: Claude implemented the file-based storage service by directly formatting raw inputs (e.g., `email`) into file paths like `f"data/users/{email}.json"` without input sanitization or path canonicalization.
- **My Challenge / Discovery**: I caught this security vulnerability during code review — relying on raw user input for filesystem paths exposes the application to **Path Traversal Attacks** (e.g., malicious input like `../../other_file` escaping the `data/users/` folder to access or overwrite arbitrary files on disk) and invalid filename crashes.
- **Final Decision**: Implemented strict security validations across storage service and auth routes:
  - Enforced RFC-compliant email regex validation (`is_valid_email`) and name sanitization with Unicode support and length limits (2–100 chars).
  - Sanitized filenames via regex replacement (`re.sub(r'[^a-zA-Z0-9@._-]', '_', email)`).
  - Added canonical path validation using `os.path.realpath` ensuring `real_path.startswith(base_path)`.
- **Trade-off**: Additional validation overhead per request, but guarantees 100% protection against directory traversal attacks on a DB-less JSON storage setup.

---

## 5. Step 3 Portrait Generation Gaps (User Caught AI Mistake #2)

- **Context & AI Code**: The AI implemented Step 3 portrait generation with sequential loops.
- **My Challenge / Discovery**: I caught three critical bugs in the AI's implementation of Step 3 during execution review:
  1. **No Image Validation (Bug / Reliability)**: The AI wrote raw image bytes directly to disk without validating the file size, headers, or checking for file corruption.
  2. **No Guarantee `portraits` Matches `characters` (Logic Bug)**: In the generation loop, if one character's portrait failed to generate, the AI silently skipped it and marked the step complete, leaving the project in an incomplete state.
  3. **No 429 Error Handling (Error Handling)**: The API returned a 500 error immediately on rate limits without any graceful handling or user-controlled retries.
- **Final Decision**: Implemented robust safeguards directly in the backend pipeline:
  1. Added header signature verification (`PNG`/`JPEG`) and minimum file size checks (>100 bytes) in `_save_image` to prevent corrupt files.
  2. Enforced transactional completion in Step 3/5: any partial failure raises a `RuntimeError` immediately, setting the step to `FAILED` so the user is forced to retry the step, avoiding incomplete project states.
  3. Added rate-limiting (429) detection in exception catch blocks, returning explicit 429 status codes with actionable advice for user-triggered retries.
- **Trade-off**: Increases lines of code and validation checks, but guarantees a highly reliable and bulletproof generation flow.

---

## 6. Race Condition on Duplicate Requests (AI Proposal Rejected #3)

- **Context & AI Code**: The AI only used state-based lock (reading/writing to JSON file) without any in-memory lock.
- **My Challenge / Discovery**: I rejected this approach. When two duplicate requests arrive almost simultaneously, both read `step_state = IDLE` before the first request can write `RUNNING` to disk. This causes both requests to run in parallel, calling Gemini twice, wasting tokens, and causing data corruption/overlapping updates.
- **Final Decision**: Implemented a 3-layer protection:
  1. **In-memory lock** (`asyncio.Lock`) - Prevents duplicate requests within the same process.
  2. **File lock** (`filelock`) - Prevents concurrent writes across processes.
  3. **Optimistic locking** (version field) - Detects conflicts during read/write operations.
- **Trade-off**: Adds complexity, but guarantees no duplicate API calls and 100% data safety against race conditions.

---

## 7. Short Polling vs. WebSockets & Unblocking the Event Loop (AI Proposal Rejected #4)

- **Context & AI Proposal**: Claude initially suggested setting up WebSockets to stream real-time progress updates from the backend to the frontend (e.g. as individual portraits or illustrations finish).
- **My Challenge / Rejection**: I rejected WebSockets. Setting up stateful WebSocket connections adds significant architectural complexity (managing connection lifecycles, authentication over WS, automatic reconnection logic, and scaling stateful servers) for an application whose database is a stateless set of JSON files on disk. Polling is simple, stateless, automatically recovers from network drops, and fits our file-based database perfectly.
- **The Bug We Caught**: When we tested the polling implementation, we realized that during long-running generation steps (which took 15-30s), all polling requests (`GET /api/projects/{id}`) and navigation requests on the frontend would **hang indefinitely** showing a loading spinner. The AI had implemented the route handlers as `async def` but executed the heavy LLM/image generation calls synchronously, blocking FastAPI's single-threaded event loop.
- **Final Decision**: We kept the stateless Short Polling mechanism (`useProjectPolling` polling every 2-2.5s) but resolved the event loop hang on the backend:
  - Delegated all 5 blocking generation steps in `steps.py` to a background threadpool using `await asyncio.to_thread(...)`.
  - This immediately unblocks FastAPI's main thread, allowing the backend to process concurrent polling requests and frontend navigation immediately while generation runs in the background.
- **Trade-off**: Polling creates slightly more HTTP network overhead than a persistent WebSocket, but it is extremely simple, robust, stateless, and 100% responsive.

---

## If you had one more day, what would you build next and why?

If I had one more day, I would build two things:

### A. Real-Time Step Updates using Server-Sent Events (SSE)

Currently, the frontend uses short-polling (every 2.5 seconds) to fetch the latest project state while steps are `RUNNING`. This creates extra network overhead and introduces up to 2.5 seconds of lag between a step's backend completion and the frontend UI update. By implementing SSE, the backend could push updates instantly (e.g., when a single portrait is saved) to the frontend. This would make the step transitions feel incredibly fast, responsive, and fluid, improving the UX without loading the server with repetitive poll requests. Additionally, I would add a **retry attempt history log** to the UI, allowing the user to view past rate-limiting failures or timeouts, enhancing the auditability of the pipeline.

---

### B. Full End-to-End Integration Test Suite

The existing test suite in `backend/tests/test_pipeline.py` covers each pipeline step **individually**, seeding pre-built project fixtures to test a single step in isolation. What's missing is a true **end-to-end integration test** that walks through the entire 5-step pipeline from scratch — from project creation to final illustration — validating the full data flow and state transitions in one continuous test run.

#### Backend: `test_full_pipeline_e2e`

I would add a single test function `test_full_pipeline_e2e` in `backend/tests/test_pipeline.py` that:

1. **Creates** a project via `POST /api/projects` and asserts `status == CREATED`.
2. **Runs Step 1 (Style)** via `POST /api/projects/{id}/steps/style` and asserts `status == STYLE_SET`.
3. **Runs Step 2 (Characters)** and asserts `status == CHARACTERS_GENERATED`, `len(characters) <= 2`, and each character has a non-empty `image_prompt`.
4. **Runs Step 3 (Portraits)** and asserts `status == PORTRAITS_GENERATED`, `len(portraits) == len(characters)`, and each portrait has a valid `/images/...` path that returns `200 image/png` from `GET /api/images/{id}/portraits/{name}`.
5. **Runs Step 4 (Chapters)** and asserts `status == CHAPTERS_GENERATED`, `len(chapters) == 1`, and the chapter has at least one character reference.
6. **Runs Step 5 (Illustrations)** and asserts `status == DONE`, `len(illustrations) == 1`, and the illustration `image_path` serves a valid PNG.
7. **Cleans up** by deleting the generated project file from disk after the test.

This test serves as a **smoke test for the entire generation pipeline** and would catch cross-step data contract bugs (e.g., Step 4 expecting `portraits` populated by Step 3) that individual step tests cannot catch in isolation.
