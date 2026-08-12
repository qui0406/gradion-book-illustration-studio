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
platform darwin -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/anhqui/Documents/gradion-book-illustration-studio/backend
plugins: anyio-4.14.2
collected 16 items

tests/test_pipeline.py ................                                  [100%]

=========================== 16 passed in 12.50s ================================
```

### Frontend Vitest Results
```text
 RUN  v1.75.0 /Users/anhqui/Documents/gradion-book-illustration-studio/frontend

 ✓ src/test/components.test.jsx (3 tests) 38ms
   ✓ Navbar Component (2 tests)
     ✓ renders brand and navigation links correctly
     ✓ triggers logout and redirects to auth page
   ✓ Footer Component (1 test)
     ✓ renders Gradion branding and terms links

 Test Files  1 passed (1)
      Tests  3 passed (3)
   Start at  20:00:21
   Duration  280ms (transform 120ms, setup 18ms)
```
