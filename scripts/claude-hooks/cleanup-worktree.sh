#!/usr/bin/env bash
# WorktreeRemove hook: clean up temporary resources when leaving a worktree
WORKTREE_PATH="${CLAUDE_WORKTREE_PATH:-$(pwd)}"

# Clean up any temp files created during worktree session
if [ -d "$WORKTREE_PATH/.claude/agent-comms" ]; then
    rm -rf "$WORKTREE_PATH/.claude/agent-comms"/* 2>/dev/null
fi

# Log removal
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Worktree cleaned: $WORKTREE_PATH" >> "$HOME/.claude/worktree-cleanup.log"
