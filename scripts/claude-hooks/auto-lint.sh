#!/usr/bin/env bash
# Auto-lint files after edit
# Python: ruff (fast linter) | JS: eslint

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"//')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

case "$FILE_PATH" in
    *.py)
        # Use ruff if available (fast Python linter), fall back to flake8
        if command -v ruff &> /dev/null; then
            LINT_OUTPUT=$(ruff check --fix "$FILE_PATH" 2>&1)
            if [ -n "$LINT_OUTPUT" ]; then
                echo "$LINT_OUTPUT" | tail -10
            fi
        elif command -v flake8 &> /dev/null; then
            LINT_OUTPUT=$(flake8 "$FILE_PATH" --max-line-length=120 2>&1)
            if [ -n "$LINT_OUTPUT" ]; then
                echo "$LINT_OUTPUT" | tail -10
            fi
        fi
        ;;
    frontend/src/*.js|frontend/src/*.jsx|frontend/src/*.ts|frontend/src/*.tsx)
        REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
        if [ -f "$REPO_DIR/frontend/node_modules/.bin/eslint" ]; then
            cd "$REPO_DIR/frontend"
            LINT_OUTPUT=$(npx eslint --fix "$FILE_PATH" 2>&1)
            if [ -n "$LINT_OUTPUT" ]; then
                echo "$LINT_OUTPUT" | tail -10
            fi
        fi
        ;;
esac

exit 0
