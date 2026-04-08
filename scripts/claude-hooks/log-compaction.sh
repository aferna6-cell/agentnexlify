#!/usr/bin/env bash
# PostCompact hook: log context compaction events for debugging
LOG_DIR="$HOME/.claude/compaction-logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
echo "[${TIMESTAMP}] Context compacted in $(pwd)" >> "$LOG_DIR/compactions.log"
