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

## 3. Envelope API Response Format with User Context (AI Proposal Rejected)

- **Context & AI Proposal**: Claude initially proposed returning a flat JSON array for `GET /api/projects?email=`, where every project item duplicated `"user_email": "user@example.com"`.
- **My Challenge / Rejection**: I rejected returning a flat array — repeating `user_email` on every single project in the array creates unnecessary data duplication and denormalization. Furthermore, a flat array lacks top-level owner context (e.g., user name and email).
- **Final Decision**: Restructured the response into an **Envelope Wrapper format**:
  - Top-level keys contain owner info (`email`, `name`).
  - An inner `"data": [...]` array contains the list of user projects.
- **Trade-off**: Adds one level of nesting (`response.data`), requiring the frontend to unwrap `data`, but eliminates redundant `user_email` fields across array items and provides clean, normalized user context.


