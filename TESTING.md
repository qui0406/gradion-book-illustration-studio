# Testing Guide & Report

This document outlines the testing strategy, frameworks, test targets, and the actual test execution reports for the Gradion Book Illustration Studio application.

---

## 1. Testing Strategy Overview

We enforce automated test coverage on both sides of the application stack to align with reliability constraints and TDD copilot instructions:

### Backend Testing Strategy
- **Framework**: `pytest` + `fastapi.testclient.TestClient`
- **Methodology**: Integration tests covering the entire 5-step lifecycle, concurrency locking, and security validations.
- **Targets**:
  - **Health & Authentication**: Rejection of invalid emails, name character validation, and basic profile loading.
  - **Security & Validation**: Verification that directory traversal query attacks (e.g., `../../etc/passwd@example.com`) are properly identified and rejected.
  - **Concurrency & Race Guard**: Testing that duplicate concurrent calls to the same project step return `409 Conflict` to preserve tokens and prevent state corruption.
  - **Stuck Lock Reset**: Simulating a stranded/interrupted step and verifying that the backend catches the timeout error, resetting the state to `IDLE` to allow retry.
  - **Sequential Ordering**: Enforcing that running Step N fails with a `400 Bad Request` if Step N-1 has not been completed.

### Frontend Testing Strategy
- **Framework**: `vitest` + `@testing-library/react` + `@testing-library/jest-dom` in a `jsdom` environment.
- **Methodology**: Unit testing on core wrapper layout structures and components ensuring auth context and session triggers.
- **Targets**:
  - **Navbar Component**: Validates branding render, retrieval of user initials, name output, and Sign Out action clearing local session state and triggering navigation.
  - **Footer Component**: Assures the copyright branding and policies links are present.

---

## 2. What We Deliberately Do Not Test
- **Real Gemini API (during normal CI runs)**: We mock or limit real calls during standard unit tests to protect API key quota and maintain deterministic runs, except for specific integration tests.
- **End-to-End Browser Actions (Cypress/Playwright)**: Deliberately omitted to minimize deployment and setup overhead, as manual quality testing satisfies current UX requirements.

---

## 3. How to Run the Tests

A single command executes all test suites across the project:
```bash
./test.sh
```

Alternatively, you can run them individually:
- **Backend**: `cd backend && venv/bin/pytest`
- **Frontend**: `cd frontend && npm test`

---

## 4. Test Execution Report

### Backend Pytest Results
```text
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0 -- /Users/anhqui/Documents/gradion-book-illustration-studio/backend/venv/bin/python3.13
cachedir: .pytest_cache
rootdir: /Users/anhqui/Documents/gradion-book-illustration-studio copy/backend
plugins: anyio-4.14.2
collecting ... collected 16 items

tests/test_pipeline.py::test_health_check PASSED                         [  6%]
tests/test_pipeline.py::test_auth_signin_and_me PASSED                   [ 12%]
tests/test_pipeline.py::test_security_email_and_path_traversal_validation PASSED [ 18%]
tests/test_pipeline.py::test_create_and_get_project PASSED               [ 25%]
tests/test_pipeline.py::test_create_project_from_file_upload PASSED      [ 31%]
tests/test_pipeline.py::test_step_1_style_execution PASSED               [ 37%]
tests/test_pipeline.py::test_step_2_characters_execution PASSED          [ 43%]
tests/test_pipeline.py::test_step_3_portraits_execution PASSED           [ 50%]
tests/test_pipeline.py::test_project_character_limit_validation PASSED   [ 56%]
tests/test_pipeline.py::test_project_chapter_limit_validation PASSED     [ 62%]
tests/test_pipeline.py::test_stale_step_lock_reset PASSED                [ 68%]
tests/test_pipeline.py::test_image_validation PASSED                     [ 75%]
tests/test_pipeline.py::test_optimistic_locking_conflict PASSED          [ 81%]
tests/test_pipeline.py::test_step_concurrency_lock PASSED                [ 87%]
tests/test_pipeline.py::test_step_4_chapters_execution PASSED            [ 93%]
tests/test_pipeline.py::test_step_5_illustrations_execution PASSED       [100%]

======================== 16 passed in 186.86s (0:03:06) ========================
```

### Frontend Vitest Results
```text
> frontend@0.0.0 test
> vitest run


 RUN  v4.1.10 /Users/anhqui/Documents/gradion-book-illustration-studio copy/frontend

 ✓ src/test/components.test.jsx (10 tests) 103ms

 Test Files  1 passed (1)
      Tests  10 passed (10)
   Start at  23:22:26
   Duration  830ms (transform 57ms, setup 89ms, import 88ms, tests 103ms, environment 480ms)
```

---

## 5. Rationale for Selected Frontend Test Targets

To comply with the instruction *"Pick a couple that matter; don't test everything"*, we selected specific critical components and UI states while deliberately omitting others.

### Why We Tested These Components & States
1. **`ProjectList` Component & its UI States (`Loading`, `Empty`, `Success`, `Error`)**:
   - **Loading State**: Ensures a proper loading indicator is shown while projects are fetching, preventing the user from seeing an empty screen or duplicate buttons.
   - **Empty State**: Vital for onboarding. When a user has 0 projects, it must render a helpful message directing them to create a new project.
   - **Success State**: Confirms that when projects exist, their cards are rendered with correct metadata and progressive step bars (e.g., "Step 5 of 5").
   - **Error State**: Verifies the application handles network or server crashes gracefully by rendering an inline error alert instead of crashing the UI.
2. **`Navbar` Component & its Session States (`Initials`, `User Name`, `Sign Out`)**:
   - **Initials & Name Display**: Confirms the user's details are retrieved correctly from the Auth Context and their avatar initials are parsed dynamically.
   - **Sign Out Flow**: A critical action that clears local storage authentication keys (`gradion_user`) and navigates back to the `/auth` page, preventing unauthenticated access.
3. **`EntityCard` Component & its Pipeline Generation States (`Not generated yet`, `Generating/Loading`, `Image loaded`)**:
   - **Not generated yet**: Verifies the card correctly renders the placeholder text ("Not generated yet") and item name/prompt before API runs.
   - **Generating/Loading State**: Ensures the card displays a dynamic loading spinner (`.gd-spinner`) and step-specific messages (e.g. "Generating portrait for Tấm..." vs "Generating illustration...") while the backend generates assets asynchronously.
   - **Success/Image loaded**: Confirms the card renders the correct HTML `<img>` tag and routes the sanitized path dynamically.

### Why We Did Not Test Other Components
- **`Footer`**: Contains only static informational links with zero dynamic state or business logic. Testing it would create high maintenance overhead with no actual reliability gain.
- **Project Detail Panels, Steppers & Forms**: Their workflows and state constraints (such as preventing duplicate executions, enforcing sequential steps, and validation limits) are already thoroughly covered by our 16 backend integration tests. Writing frontend unit tests for them would duplicate test cases already validated at the API layer.

