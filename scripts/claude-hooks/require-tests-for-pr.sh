#!/usr/bin/env bash
# Block PR creation unless all tests pass
# Exit 2 = blocked, Claude must fix tests first

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Drain stdin — read from fd 0 directly; avoids /dev/stdin device unavailable in MCP context
cat > /dev/null 2>&1 || true

echo "Running test suite before PR creation..."

cd "$REPO_DIR"

# Find pytest — python3 -m pytest if pytest importable, else system pytest, else warn+skip
if python3 -c "import pytest" 2>/dev/null; then
    PYTEST_CMD="python3 -m pytest"
elif command -v pytest &>/dev/null; then
    PYTEST_CMD="pytest"
else
    echo "WARNING: pytest not found in python3 or PATH — skipping Python test check." >&2
    PYTEST_CMD=""
fi

# Run Python tests
if [ -n "$PYTEST_CMD" ] && ls tests/test_*.py &>/dev/null; then
    if ! $PYTEST_CMD tests/ -x --tb=short -q 2>&1; then
        echo "BLOCKED: Python tests are failing. Fix all test failures before creating a PR." >&2
        exit 2
    fi
fi

# Check frontend build — capture output + exit code separately (pipe hides exit code)
if [ -f "frontend/package.json" ]; then
    echo "Checking frontend build..."
    BUILD_OUTPUT=$(cd "$REPO_DIR/frontend" && npm run build --silent 2>&1)
    BUILD_EXIT=$?
    if [ "$BUILD_EXIT" -ne 0 ]; then
        echo "$BUILD_OUTPUT" | tail -10
        echo "BLOCKED: Frontend build is failing. Fix build errors before creating a PR." >&2
        exit 2
    fi
fi

echo "All checks passed. PR creation allowed."
exit 0
