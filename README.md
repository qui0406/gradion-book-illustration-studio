# Gradion Book Illustration Studio

An elegant full-stack application that transforms any book excerpt into a series of visual character portraits and chapter illustrations using the Google Gemini API. The pipeline runs sequentially in 5 user-controlled steps: **Style Definition → Character Extraction → Portrait Generation → Chapter Extraction → Scene Illustration**.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Running the Project](#running-the-project)
- [Running the Test Suites](#running-the-test-suites)
- [Architecture & Design Overview](#architecture--design-overview)
- [Environment Variables](#environment-variables)

---

## Prerequisites
Ensure the following tools are installed locally:
- **Node.js** (v18.0 or later) & npm
- **Python** (v3.11 or later)
- **pip** and virtualenv package manager

---

## Local Development Setup

To initialize the project for local development:

1. Clone this repository to your workspace.
2. Setup the backend virtualenv:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd ..
   ```
3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   cd ..
   ```
4. Setup environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and insert your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_real_gemini_api_key_here
   ```

---

## Running the Project

To start both backend and frontend applications concurrently using a single command:
```bash
./start.sh
```
This script boots:
- **Backend API**: Running on [http://localhost:8000](http://localhost:8000)
- **Frontend App**: Running on [http://localhost:5173](http://localhost:5173)

---

## Running the Test Suites

To execute the automated unit and integration tests across both the backend and frontend:
```bash
./test.sh
```
This runs:
- **Backend Tests**: `pytest` covering API routes, concurrency locks, path traversal protections, state validation, and Gemini integrations.
- **Frontend Tests**: `vitest` covering layout, navigation, auth context state management, and key component rendering.

---

## Architecture & Design Overview

- **Frontend**: React (Vite) styled using Vanilla CSS following the exact **Gradion Design System** tokens (colors, animations, stepper, card layout). Includes an Auth context session store in `localStorage` and status polling via React Hooks.
- **Backend**: FastAPI (Python) routing requests sequentially. Uses the official Google `google-genai` SDK.
- **Data Persistence**: Lightweight JSON file-on-disk storage (`data/projects/` and `data/users/`) protected by multi-layered concurrency mechanisms:
  1. **In-memory lock**: `asyncio.Lock` per project.
  2. **File lock**: `filelock` library protecting against concurrent filesystem writes.
  3. **Optimistic locking**: A `version` number check detecting simultaneous modifications.
- **Image Validation**: Sanitizes and validates image bytes headers (`PNG`/`JPEG`) before persistence to block corrupted responses.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Google Gemini API credentials | Required |
| `VITE_API_URL` | Base API target URL for the frontend client | `http://localhost:8000` |
