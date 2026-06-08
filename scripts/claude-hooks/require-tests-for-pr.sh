#!/usr/bin/env bash
# Block PR creation unless all tests pass
# Exit 2 = blocked, Claude must fix tests first

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Drain stdin
cat < /dev/stdin > /dev/null 2>&1

cd "$REPO_DIR"

# Docs-only exemption: if the branch changes no executable code vs the default
# branch, skip the test + build gate. A markdown/doc PR can't break tests, and
# a blanket gate here false-blocks doc PRs (e.g. when pytest isn't installed).
DEFAULT_BRANCH="$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
CHANGED_FILES="$(git diff --name-only "origin/${DEFAULT_BRANCH}...HEAD" 2>/dev/null)"
if [ -n "$CHANGED_FILES" ] && ! echo "$CHANGED_FILES" | grep -qE '\.(py|js|jsx|ts|tsx|mjs|cjs|sql)$'; then
    echo "Docs-only change (no code files vs ${DEFAULT_BRANCH}). Skipping test gate."
    exit 0
fi

echo "Running test suite before PR creation..."

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
