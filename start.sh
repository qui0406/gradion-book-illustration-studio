#!/usr/bin/env bash

set -e

# Cleanup child processes on exit
cleanup() {
  echo ""
  echo "Shutting down backend and frontend services..."
  kill 0 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM EXIT

echo "Starting Gradion Book Illustration Studio..."

# Start Backend
echo "Starting Backend (FastAPI)..."
cd backend
if [ -d "venv/Scripts" ]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start Frontend
echo "Starting Frontend (Vite + React)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Services started:"
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:5173"

wait $BACKEND_PID $FRONTEND_PID
