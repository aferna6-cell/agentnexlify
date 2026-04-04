#!/usr/bin/env bash
# Run tests after every code edit
# Only triggers for Python and JS source files (not docs, configs, etc.)

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"//')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

case "$FILE_PATH" in
    *.py)
        # Only run if there are test files
        if ls "$REPO_DIR"/tests/test_*.py &>/dev/null; then
            echo "Running Python tests..."
            cd "$REPO_DIR" && python3 -m pytest tests/ -x --tb=short -q 2>&1 | tail -8
        fi
        ;;
    frontend/src/*.js|frontend/src/*.jsx|frontend/src/*.ts|frontend/src/*.tsx)
        # Only run if npm test is configured
        if [ -f "$REPO_DIR/frontend/package.json" ] && grep -q '"test"' "$REPO_DIR/frontend/package.json" 2>/dev/null; then
            echo "Running frontend tests..."
            cd "$REPO_DIR/frontend" && npm run test --silent 2>&1 | tail -5
        fi
        ;;
esac

# Always exit 0 — test failures are informational, not blocking
exit 0
