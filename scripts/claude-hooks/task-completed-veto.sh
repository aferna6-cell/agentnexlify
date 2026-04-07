#!/usr/bin/env bash
# TaskCompleted hook — vetoes completion if tests are failing
# Exit code 2 = block completion with feedback
set -euo pipefail

cd /home/aidan/agentnexlify

# Check if frontend builds
if [ -d "frontend" ]; then
  BUILD_OUTPUT=$(cd frontend && npx vite build --mode production 2>&1) || {
    echo '{"decision":"block","reason":"Frontend build is failing. Fix build errors before marking task complete.","systemMessage":"Task completion blocked: frontend build fails"}' >&2
    exit 2
  }
fi

# Check for Python syntax errors in backend
if [ -d "backend" ]; then
  SYNTAX_ERRORS=$(python3 -m py_compile backend/main.py 2>&1) || {
    echo '{"decision":"block","reason":"Backend has syntax errors. Fix before marking complete.","systemMessage":"Task completion blocked: backend syntax errors"}' >&2
    exit 2
  }
fi

exit 0
