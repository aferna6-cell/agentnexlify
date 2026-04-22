#!/usr/bin/env bash
# Context budget monitor. Warns at 250k tokens (25% of 1M pin), forces handoff at 400k.
# Reads transcript_path from hook stdin JSON, estimates tokens from byte count (~4 chars/token).
# Rule: .claude/rules/one-task-one-chat.md — 1M context is a noob trap, stay <25%.
set -euo pipefail

# Warn + force thresholds in approximate tokens
WARN_TOKENS=250000
FORCE_TOKENS=400000

# Approximate chars per token (conservative — real ratio varies by content)
CHARS_PER_TOKEN=4
WARN_BYTES=$((WARN_TOKENS * CHARS_PER_TOKEN))
FORCE_BYTES=$((FORCE_TOKENS * CHARS_PER_TOKEN))

# Read hook stdin (JSON with transcript_path)
INPUT=$(cat)

# Extract transcript_path — fall back gracefully if missing or jq absent
TRANSCRIPT_PATH=""
if command -v jq >/dev/null 2>&1; then
  TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)
fi

# Nothing to measure → exit silently
if [[ -z "$TRANSCRIPT_PATH" ]] || [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  exit 0
fi

# Measure
BYTES=$(wc -c < "$TRANSCRIPT_PATH" 2>/dev/null | tr -d ' ')
[[ "$BYTES" =~ ^[0-9]+$ ]] || exit 0

# Estimate tokens
TOKENS=$((BYTES / CHARS_PER_TOKEN))

# Emit directive based on threshold
if (( BYTES >= FORCE_BYTES )); then
  MSG="CONTEXT BUDGET EXCEEDED (~${TOKENS} tokens, ~$((TOKENS * 100 / 1000000))% of 1M). Force handoff NOW before answering. Rule: .claude/rules/one-task-one-chat.md. Steps: (1) Run /checkpoint to save state, (2) Generate 5-part handoff summary, (3) Tell user to start fresh session with /recover. Do not continue in this session — quality degrades past 40%% context. Quote this threshold in the handoff."
  printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$MSG"
elif (( BYTES >= WARN_BYTES )); then
  MSG="CONTEXT BUDGET WARNING (~${TOKENS} tokens, ~$((TOKENS * 100 / 1000000))% of 1M, threshold 25%%). Claude Code quality degrades past 25%% context (per MAG7-adjacent senior-engineer 120hr benchmark). Options: (1) Finish current subtask and /checkpoint, (2) Compact with /compact if task still active, (3) Stay under ${WARN_TOKENS} tokens for rest of session. Rule: .claude/rules/one-task-one-chat.md."
  printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$MSG"
fi

exit 0
