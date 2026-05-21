#!/usr/bin/env bash
# Block PR creation unless all relevant tests pass.
# Exit 2 = blocked, Claude must fix tests first.
# Docs-only PRs skip the gate. Missing test tooling defers to CI rather than
# falsely blocking (CI runs the real suite).

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Drain stdin (hook receives JSON on fd 0; /dev/stdin is not a device everywhere)
cat >/dev/null 2>&1

cd "$REPO_DIR" || exit 0

# Base ref for the change-set diff
BASE="main"
git rev-parse --verify origin/main >/dev/null 2>&1 && BASE="origin/main"
CHANGED="$(git diff --name-only "$BASE"...HEAD 2>/dev/null)"

# Docs-only PR — no code touched, skip the test/build gate
if [ -n "$CHANGED" ] && ! echo "$CHANGED" | grep -qE '\.(py|jsx?|tsx?|css)$|^frontend/'; then
    echo "Docs-only change set — test/build gate skipped."
    exit 0
fi

echo "Running test suite before PR creation..."

# Python tests — only when pytest is actually available
if ls tests/test_*.py &>/dev/null; then
    if python3 -m pytest --version &>/dev/null; then
        if ! python3 -m pytest tests/ -x --tb=short -q 2>&1; then
            echo "BLOCKED: Python tests are failing. Fix all test failures before creating a PR." >&2
            exit 2
        fi
    else
        echo "WARN: pytest not installed in this environment — Python test gate deferred to CI." >&2
    fi
fi

# Frontend build — only when npm + node_modules are available
if [ -f "frontend/package.json" ]; then
    if command -v npm &>/dev/null && [ -d "frontend/node_modules" ]; then
        echo "Checking frontend build..."
        cd "$REPO_DIR/frontend" || exit 0
        if ! npm run build --silent 2>&1 | tail -3; then
            echo "BLOCKED: Frontend build is failing. Fix build errors before creating a PR." >&2
            exit 2
        fi
    else
        echo "WARN: npm or node_modules unavailable — frontend build gate deferred to CI." >&2
    fi
fi

echo "All checks passed. PR creation allowed."
exit 0
