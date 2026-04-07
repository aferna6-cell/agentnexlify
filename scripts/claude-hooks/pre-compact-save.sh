#!/usr/bin/env bash
# Pre-compaction hook — saves critical state AND injects context into the compaction summary.
# The hookSpecificOutput JSON ensures key state survives into the compacted context.

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CHECKPOINT_FILE="$REPO_DIR/.claude/agent-comms/checkpoint.md"
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')

# Gather single-line summaries safe to embed in JSON
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
GIT_LOG=$(git log --oneline -5 2>/dev/null | tr '\n' ' | ' | sed 's/ | $//' || echo "no history")
GIT_DIFF=$(git diff --stat 2>/dev/null | tail -1 || echo "clean")
GIT_STAGED=$(git diff --cached --stat 2>/dev/null | tail -1 || echo "nothing staged")
AGENT_OUTPUTS=$(ls -1 "$REPO_DIR/.claude/agent-comms/"*.md 2>/dev/null | grep -v README | grep -v checkpoint | xargs -I{} basename {} 2>/dev/null | tr '\n' ', ' | sed 's/, $//' || echo "none")

# Save full checkpoint file
cat > "$CHECKPOINT_FILE" << EOF
## Auto-Checkpoint — $TIMESTAMP
**Reason:** Context compaction triggered
**Branch:** $BRANCH

### Recent Commits
$(git log --oneline -5 2>/dev/null || echo "No git history available")

### Uncommitted Changes
$(git diff --stat 2>/dev/null || echo "Clean")

### Staged Files
$(git diff --cached --stat 2>/dev/null || echo "Nothing staged")

### Agent Outputs Present
$(ls -1 "$REPO_DIR/.claude/agent-comms/"*.md 2>/dev/null | grep -v README | grep -v checkpoint || echo "None")

---
*Auto-saved before compaction. Run /recover to restore full context.*
EOF

# Inject summary into compaction context so key state survives the trim.
# Claude Code includes hookSpecificOutput in what it compacts over, so this
# gets baked into the compaction summary rather than being lost.
printf '{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"COMPACTION STARTING. Snapshot: branch=%s | recent=%s | diff=%s | staged=%s | agents=%s | checkpoint saved to .claude/agent-comms/checkpoint.md. After compaction, read that file or run /recover to restore context."}}\n' \
    "$BRANCH" "$GIT_LOG" "$GIT_DIFF" "$GIT_STAGED" "$AGENT_OUTPUTS"

exit 0
