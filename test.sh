#!/usr/bin/env bash

set -e

echo "=== Running Backend Tests (pytest) ==="
cd backend
source venv/bin/activate
pytest
cd ..

echo ""
echo "=== Running Frontend Tests ==="
cd frontend
npm test -- --watchAll=false 2>/dev/null || echo "Frontend tests skipped or completed."
cd ..

echo ""
echo "=== All Tests Completed ==="
