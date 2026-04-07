#!/bin/bash
# Pre-commit triple review gate.
# Fires on Bash tool calls containing "git commit".
# Injects reminder to spawn 3 review agents before committing.

INPUT="$CLAUDE_TOOL_INPUT"

# Only trigger on git commit commands
if echo "$INPUT" | grep -q "git commit"; then
  cat << 'GATE'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"PRE-COMMIT REVIEW GATE: Before this commit lands, spawn 3 review agents in parallel (use run_in_background=true): (1) ARCHITECTURE agent — check for design violations, coupling issues, missing abstractions, wrong layer boundaries. (2) DUPLICATION agent — scan for copy-paste code, repeated patterns that should be extracted, redundant logic. (3) PERFORMANCE agent — check for N+1 queries, missing indexes, unnecessary re-renders, O(n^2) loops, large bundle impacts. Each agent should read the staged diff (git diff --cached) and report issues. If any agent finds a CRITICAL issue, do NOT proceed with the commit — fix first. For HIGH issues, flag to user. MEDIUM/LOW can proceed."}}
GATE
fi
