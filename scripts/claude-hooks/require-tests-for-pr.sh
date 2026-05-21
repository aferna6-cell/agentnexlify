#!/usr/bin/env bash
# Block PR creation unless all tests pass
# Exit 2 = blocked, Claude must fix tests first

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Drain stdin
cat < /dev/stdin > /dev/null 2>&1

echo "Running test suite before PR creation..."

cd "$REPO_DIR"

# Run Python tests
if ls tests/test_*.py &>/dev/null; then
    if ! python3 -m pytest tests/ -x --tb=short -q 2>&1; then
        echo "BLOCKED: Python tests are failing. Fix all test failures before creating a PR." >&2
        exit 2
    fi
fi

# Check frontend build
if [ -f "frontend/package.json" ]; then
    echo "Checking frontend build..."
    cd "$REPO_DIR/frontend"
    if ! npm run build --silent 2>&1 | tail -3; then
        echo "BLOCKED: Frontend build is failing. Fix build errors before creating a PR." >&2
        exit 2
    fi
fi

echo "All checks passed. PR creation allowed."
exit 0
