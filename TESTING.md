# Testing Guide & Report

This document outlines the testing strategy, test targets, storage isolation mechanisms, and current test execution reports for the Gradion Book Illustration Studio application.

---

## 1. Testing Strategy Overview

We enforce automated test coverage across the full application stack to ensure reliability, security, and performance constraints:

### Backend Testing Strategy
- **Framework**: `pytest` + `fastapi.testclient.TestClient`
- **Methodology**: Integration & unit tests covering the 5-step pipeline lifecycle, concurrency locking, file lock synchronization, data storage isolation, and security/ownership enforcement.
- **Key Test Targets**:
  - **Health & Authentication**: User signin, profile registration, identity validation, and email security.
  - **Security & Ownership**: Server-side verification enforcing `401 Unauthorized` for unauthenticated requests and `403 Forbidden` for cross-user project or asset access attempts.
  - **Data Storage Isolation**: Pytest `autouse` fixture redirecting data storage to temporary directories (`tmp_path`), guaranteeing test runs never modify or delete real application data.
  - **Fake Full-Pipeline Integration**: End-to-end execution of all 5 steps (`CREATED` → `STYLE_SET` → `CHARACTERS_GENERATED` → `PORTRAITS_GENERATED` → `CHAPTERS_GENERATED` → `DONE`) using mocked Gemini API dependencies.
  - **Immediate Progress Persistence & Retry Skip**: Verification that portrait and illustration progress is saved to disk immediately after each image, and already-generated valid images are skipped upon retrying.
  - **Adult-Only Character Age Validation**: Verification that characters under 18 are rejected by backend Pydantic schema validation (`age: int = Field(ge=18)`).
  - **Concurrency & Race Guard**: Verification that duplicate concurrent calls to an active step return `409 Conflict`.
  - **Stale Lock Auto-Reset**: Verification that stuck steps past timeout limits auto-reset `step_state` to `IDLE` to allow user retries.

### Frontend Testing Strategy
- **Framework**: `vitest` + `@testing-library/react` + `@testing-library/jest-dom` in a `jsdom` environment.
- **Methodology**: Component unit testing and user flow integration testing.
- **Key Test Targets**:
  - **Navbar Component**: Branding render, user avatar initials, name output, and Sign Out session clearing.
  - **ProjectList Component**: Loading spinners, empty state display, project list rendering, and error handling.
  - **EntityCard Component**: "Not generated yet" empty state, loading spinner, and image rendering.
  - **ProjectDetail & Orchestration**: Step panel transitions, `useProjectPolling` state polling, stuck step detection, and Retry button behavior.

---

## 2. Technical Safeguards & Architecture Highlights

1. **Non-blocking Event Loop (`asyncio.to_thread`)**:
   All synchronous Google GenAI SDK calls are offloaded to worker threads via `await asyncio.to_thread(...)`, keeping FastAPI's asyncio event loop responsive to concurrent polling (`GET /api/projects/{id}`) and image serving requests.

2. **Strict Test Reporting (`test.sh`)**:
   The test runner script executes `npm test -- --run` directly without suppressing errors, ensuring any frontend or backend test failure returns a non-zero exit code.

3. **Isolated Test Storage**:
   Pytest automatically redirects storage paths to `tmp_path` during test execution, preserving real workspace data integrity.

---

## 3. How to Run the Tests

Execute all test suites across backend and frontend using the unified test script:
```bash
./test.sh
```

Alternatively, run test suites individually:
- **Backend Tests**: `cd backend && pytest`
- **Frontend Tests**: `cd frontend && npm test -- --run`

---

## 4. Test Execution Report

### Backend Pytest Execution Summary
```text
=== Running Backend Tests (pytest) ===
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/anhqui/Documents/gradion-book-illustration-studio/backend
plugins: anyio-4.14.2
collected 21 items

tests/test_pipeline.py::test_health_check PASSED                         [  4%]
tests/test_pipeline.py::test_auth_signin_and_me PASSED                   [  9%]
tests/test_pipeline.py::test_security_email_and_path_traversal_validation PASSED [ 14%]
tests/test_pipeline.py::test_create_and_get_project PASSED               [ 19%]
tests/test_pipeline.py::test_create_project_from_file_upload PASSED      [ 23%]
tests/test_pipeline.py::test_step_1_style_execution SKIPPED              [ 28%]
tests/test_pipeline.py::test_step_2_characters_execution SKIPPED         [ 33%]
tests/test_pipeline.py::test_step_3_portraits_execution PASSED           [ 38%]
tests/test_pipeline.py::test_project_character_limit_validation PASSED   [ 42%]
tests/test_pipeline.py::test_project_chapter_limit_validation PASSED     [ 47%]
tests/test_pipeline.py::test_stale_step_lock_reset PASSED                [ 52%]
tests/test_pipeline.py::test_image_validation PASSED                     [ 57%]
tests/test_pipeline.py::test_optimistic_locking_conflict PASSED          [ 61%]
tests/test_pipeline.py::test_step_concurrency_lock PASSED                [ 66%]
tests/test_pipeline.py::test_step_4_chapters_execution PASSED            [ 71%]
tests/test_pipeline.py::test_step_5_illustrations_execution PASSED       [ 76%]
tests/test_pipeline.py::test_portrait_immediate_persistence_and_retry_skip PASSED [ 80%]
tests/test_pipeline.py::test_illustration_immediate_persistence_and_retry_skip PASSED [ 85%]
tests/test_pipeline.py::test_character_adult_only_validation PASSED     [ 90%]
tests/test_pipeline.py::test_project_ownership_and_authentication_security PASSED [ 95%]
tests/test_pipeline.py::test_fake_full_pipeline_end_to_end PASSED       [100%]

======================== 19 passed, 2 skipped in 36.03s ========================
```

### Frontend Vitest Execution Summary
```text
=== Running Frontend Tests ===

> frontend@0.0.0 test
> vitest run --run

 RUN  v4.1.10 /Users/anhqui/Documents/gradion-book-illustration-studio/frontend

 ✓ src/test/components.test.jsx (10 tests)
 ✓ src/test/orchestration.test.jsx (3 tests)

 Test Files  2 passed (2)
      Tests  13 passed (13)
   Start at  10:58:28
   Duration  888ms

=== All Tests Completed Successfully ===
```
