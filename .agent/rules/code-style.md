# Code Style Guidelines

- Backend (FastAPI):
  - Use precise Python type hints and Pydantic schemas for all incoming/outgoing data.
  - Clear module structure: `app/routes/`, `app/services/`, `app/models/`.
  - Clean separation between HTTP Controllers (routes) and Business Logic (services).

- Frontend (React + Vite):
  - Write concise Functional Components using React Hooks.
  - Feature-based directory structure: `pages/`, `components/`, `hooks/`, `api/`.
  - Manage API calls via a centralized Axios instance located in `api/client.js`.
