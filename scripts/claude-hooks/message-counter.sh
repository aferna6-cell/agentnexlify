#!/usr/bin/env bash
# Counts user prompts per session. Every 15th prompt injects a handoff-summary directive.
# State: .claude/state/message-count (plain int). Reset when user ends session / clears state.
set -euo pipefail

STATE_DIR=".claude/state"
FILE="$STATE_DIR/message-count"
mkdir -p "$STATE_DIR"
[[ -f "$FILE" ]] || echo 0 > "$FILE"

N=$(tr -d '[:space:]' < "$FILE")
[[ "$N" =~ ^[0-9]+$ ]] || N=0
N=$((N + 1))
echo "$N" > "$FILE"

if (( N % 15 == 0 )); then
  MSG="HANDOFF TRIGGER (message $N): Generate a conversation summary now BEFORE answering the user's current prompt. Format: (1) What we are working on (2) Decisions made this session (3) Files changed + key paths (4) Open questions / blockers (5) Concrete next step. This is Rule 3 from .claude/rules/user-rules.md and is non-bypassable. User pastes the summary into a fresh session to continue work."
  printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$MSG"
fi
