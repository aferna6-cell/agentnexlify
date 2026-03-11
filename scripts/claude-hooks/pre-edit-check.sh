#!/usr/bin/env bash
# Claude Code pre-edit hook
# Warns before editing sensitive files

# Read the tool input from stdin
INPUT=$(cat)

# Extract the file path being edited
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"//')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Block .env edits
if [[ "$FILE_PATH" == *.env* ]]; then
    echo "BLOCKED: Do not edit .env files. Set environment variables in Railway/Vercel directly."
    exit 2
fi

# Warn on migration edits (existing migrations should be immutable)
if [[ "$FILE_PATH" == migrations/*.sql ]]; then
    if [ -f "$FILE_PATH" ]; then
        echo "WARNING: You are editing an existing migration file. Existing migrations should be immutable. Create a new numbered migration instead."
    fi
fi

# Warn on main.py edits (CORS, router registration)
if [[ "$FILE_PATH" == *main.py ]]; then
    echo "NOTE: main.py contains CORS config and router registration. Verify both after editing."
fi

exit 0
