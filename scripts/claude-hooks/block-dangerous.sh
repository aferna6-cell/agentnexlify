#!/usr/bin/env bash
# Block dangerous commands before they execute
# Exit code 2 = blocked (Claude sees the message and tries a safer approach)

INPUT=$(cat)

cmd=$(echo "$INPUT" | grep -oP '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"command"\s*:\s*"//;s/"//')

if [ -z "$cmd" ]; then
    exit 0
fi

# Dangerous patterns
PATTERNS=(
    "rm -rf /"
    "rm -rf \."
    "rm -rf \*"
    "git reset --hard"
    "git push.*--force"
    "git push.*-f "
    "git clean -fd"
    "DROP TABLE"
    "DROP DATABASE"
    "TRUNCATE "
    "DELETE FROM.*WHERE 1"
    "curl .+\| *sh"
    "curl .+\| *bash"
    "wget .+\| *sh"
    "wget .+\| *bash"
    "chmod 777"
    "pkill -9"
    "kill -9"
    "> /dev/sd"
    "mkfs\."
    "dd if="
)

for pattern in "${PATTERNS[@]}"; do
    if echo "$cmd" | grep -qiE "$pattern"; then
        echo "BLOCKED: Command matches dangerous pattern '$pattern'. Propose a safer alternative." >&2
        exit 2
    fi
done

exit 0
