#!/usr/bin/env bash
# Auto-format every file Claude touches
# Python: black | JS/CSS/HTML: prettier

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"//')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

case "$FILE_PATH" in
    *.py)
        if command -v black &> /dev/null; then
            black --quiet "$FILE_PATH" 2>/dev/null
        fi
        ;;
    *.js|*.jsx|*.ts|*.tsx|*.css|*.html|*.json|*.yaml|*.yml)
        if command -v npx &> /dev/null; then
            npx prettier --write "$FILE_PATH" 2>/dev/null
        fi
        ;;
esac

exit 0
