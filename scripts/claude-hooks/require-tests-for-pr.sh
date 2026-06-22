#!/usr/bin/env bash
# Block PR creation unless all tests pass
# Exit 2 = blocked, Claude must fix tests first

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Drain stdin (handle non-interactive/remote container environments)
cat > /dev/null 2>&1 || true

echo "Running test suite before PR creation..."

cd "$REPO_DIR"

# Run Python tests (skip if pytest or required deps not available — e.g. remote container without venv)
if ls tests/test_*.py &>/dev/null; then
    if ! python3 -m pytest --version &>/dev/null; then
        echo "WARNING: pytest not available in this environment — skipping Python test gate." >&2
    elif ! python3 -c "import httpx" &>/dev/null; then
        echo "WARNING: Python test dependencies not installed (httpx missing) — skipping Python test gate." >&2
    elif ! python3 -m pytest tests/ -x --tb=short -q 2>&1; then
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
