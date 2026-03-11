#!/usr/bin/env bash
# Pre-compaction hook — saves critical state before context is compacted
# This runs automatically when Claude Code compacts the session

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CHECKPOINT_FILE="$REPO_DIR/.claude/agent-comms/checkpoint.md"
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')

# Only create if it doesn't already exist or is stale (>30 min old)
if [ ! -f "$CHECKPOINT_FILE" ] || [ "$(find "$CHECKPOINT_FILE" -mmin +30 2>/dev/null)" ]; then
    cat > "$CHECKPOINT_FILE" << EOF
## Auto-Checkpoint — $TIMESTAMP
**Reason:** Context compaction triggered

### Git State
$(git log --oneline -5 2>/dev/null || echo "No git history available")

### Uncommitted Changes
$(git diff --stat 2>/dev/null || echo "No uncommitted changes")

### Staged Files
$(git diff --cached --stat 2>/dev/null || echo "Nothing staged")

### Agent Outputs Present
$(ls -1 "$REPO_DIR/.claude/agent-comms/"*.md 2>/dev/null | grep -v README | grep -v checkpoint || echo "None")

---
*Auto-saved before compaction. Read this file to restore context.*
EOF
fi

exit 0
