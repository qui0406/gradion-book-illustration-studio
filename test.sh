#!/usr/bin/env bash

set -e

echo "=== Running Backend Tests (pytest) ==="
cd backend
if [ -d "venv/Scripts" ]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi
pytest
cd ..

echo ""
echo "=== Running Frontend Tests ==="
cd frontend
npm test -- --run
cd ..

echo ""
echo "=== All Tests Completed Successfully ==="

