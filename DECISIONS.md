# Architectural & Design Decisions (`DECISIONS.md`)

## AI Copilot Workflow

I built this project using Cursor with Claude 3.5 Sonnet. Each decision below originated from genuine technical discussions — sometimes proposed by me, sometimes by the AI, and always rigorously challenged before reaching the final trade-off.

---

## 1. Separating `currentStep` and `stepStatus` (AI Proposal Rejected #1)

- **Context & AI Proposal**: Claude proposed a single `status` enum to track progress (e.g., `DRAFT` → `PROCESSING_STEP_2` → `COMPLETED`).
- **My Challenge / Rejection**: I rejected this — a single enum cannot represent "Step 2 is completed, but Step 3 is currently running or failed", which is exactly what a page reload needs to read correctly.
- **Final Decision**: Split state into `currentStep` (1-5) and `stepStatus` (`idle` | `running` | `completed` | `failed`).
- **Trade-off**: Maintaining sync between two fields and handling stuck state timeouts.

---

## 2. Using JSON Files Instead of a Database (AI Challenge Accepted #1)

- **My Proposal**: I wanted to use local JSON files on disk (`data/projects/{id}.json`) to keep the system simple and avoid database setup overhead.
- **AI Counter-argument**: Claude challenged me on concurrent write risks — if a user opens two tabs and clicks "Generate", JSON files could be corrupted.
- **Final Decision**: I accepted the AI's valid challenge and added inter-process file locking via Python's `filelock` library.
- **Trade-off**: Lack of ACID transactions, but guarantees 100% data safety without DB complexity.

---

## 3. No Automatic Retry Loop on Gemini API Failures (AI Proposal Rejected #2)

- **Context & AI Proposal**: Claude proposed an auto-retry loop (`while retry < 3`) with exponential backoff on Gemini 429/5xx errors.
- **My Challenge / Rejection**: I rejected this to strictly follow the cost control requirement ("Never automatically retry a Gemini call in a loop — only the user triggers retries").
- **Final Decision**: Set `stepStatus = 'failed'` immediately on error and show an explicit "Retry" button on the UI for manual triggers.
- **Trade-off**: Users must click Retry manually during transient network glitches, but API cost is 100% controlled.

---

## 4. Sequential Image Generation Instead of Parallel Execution (AI Proposal Rejected #3)

- **Context & AI Proposal**: Claude proposed using `asyncio.gather()` to generate all character portraits and chapter scene illustrations in parallel.
- **My Challenge / Rejection**: I rejected this because parallel generation keeps the UI static without feedback for 30+ seconds, and Step 5 requires referencing Step 3 portrait images sequentially for character consistency.
- **Final Decision**: Generate images sequentially, saving PNG files to disk and updating JSON state immediately after each image for live polling feedback.
- **Trade-off**: Slightly longer total execution time, but significantly superior UX and character consistency.

---

## 5. Process Locking + Disk Timestamps for Stuck State Recovery (AI Challenge Accepted #2)

- **My Initial Idea**: I initially planned to use a simple in-memory Mutex (`threading.Lock`) to prevent duplicate execution requests within the backend process.
- **AI Counter-argument**: Claude pointed out a critical flaw — in-memory locks vanish when the server restarts or when the user reloads the page mid-execution. The project state would remain permanently stuck at `stepStatus = 'running'`. Claude proposed persisting a `stepStartedAt` timestamp on disk to enable automatic recovery.
- **Final Decision**: I found the AI's reasoning very valid and accepted the proposal. I combined both mechanisms: in-memory process locks for instantaneous request deduplication, plus a disk-persisted `stepStartedAt` timestamp. If `stepStatus === 'running'` and `now - stepStartedAt > 5 minutes`, the backend automatically resets `stepStatus = 'failed'`, allowing user retry.
- **Trade-off**: Maintaining both memory locks and disk timestamp state checks adds slight complexity, but guarantees no project is ever permanently stuck.

---

## 6. HTTP Short Polling Instead of WebSockets (AI Proposal Rejected #4)

- **Context & AI Proposal**: Claude proposed WebSockets or SSE for real-time image updates.
- **My Challenge / Rejection**: I rejected this — WebSockets add connection lifecycle overhead and state reconnect complexity on page reloads.
- **Final Decision**: Implemented 2-second HTTP short polling active only when `stepStatus === 'running'`.
- **Trade-off**: Increased HTTP request count (~15-30 requests per step), but a clean, stateless architecture.

---

## 7. Serving Images via Local Static Route, No Cloud S3 (AI Proposal Rejected #5)

- **Context & AI Proposal**: AI suggested cloud storage (S3/R2) citing production best practices.
- **My Challenge / Rejection**: I rejected this based on the spec: *"Images are stored on local filesystem, served via your own API. No S3, no blob storage, no CDN."*
- **Final Decision**: Store images in `./storage/images/` and serve via local static API routes.
- **Trade-off**: Cannot scale multi-instance production, but perfectly aligned with local scope.

---

## What would you build next if you had one more day and why?

If I had one more day, I would implement Server-Sent Events (SSE) to eliminate polling HTTP requests, and add Veo video generation to animate chapter illustrations.
