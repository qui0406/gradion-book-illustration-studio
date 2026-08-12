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
- **Final Decision**: Plan to address these reliability and logic bugs directly in the Gemini pipeline in future updates (e.g., implementing image validation, raising explicit exceptions for partial failures).
- **Trade-off**: Requires implementing robust validations and error handling in future updates.

---

## 6. Race Condition on Duplicate Requests (AI Proposal Rejected #3)

- **Context & AI Code**: The AI only used state-based lock (reading/writing to JSON file) without any in-memory lock.
- **My Challenge / Discovery**: I rejected this approach. When two duplicate requests arrive almost simultaneously, both read `step_state = IDLE` before the first request can write `RUNNING` to disk. This causes both requests to run in parallel, calling Gemini twice, wasting tokens, and causing data corruption/overlapping updates.
- **Final Decision**: Implemented a 3-layer protection:
  1. **In-memory lock** (`asyncio.Lock`) - Prevents duplicate requests within the same process.
  2. **File lock** (`filelock`) - Prevents concurrent writes across processes.
  3. **Optimistic locking** (version field) - Detects conflicts during read/write operations.
- **Trade-off**: Adds complexity, but guarantees no duplicate API calls and 100% data safety against race conditions.

