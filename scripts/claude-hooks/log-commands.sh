#!/usr/bin/env bash
# Log every Bash command Claude runs with timestamp
# Audit trail for debugging — add .claude/command-log.txt to .gitignore

INPUT=$(cat)

cmd=$(echo "$INPUT" | grep -oP '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"command"\s*:\s*"//;s/"//')

if [ -z "$cmd" ]; then
    exit 0
fi

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LOG_FILE="$REPO_DIR/.claude/command-log.txt"

printf '%s %s\n' "$(date -Is)" "$cmd" >> "$LOG_FILE"

exit 0
