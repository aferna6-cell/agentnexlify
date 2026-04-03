#!/usr/bin/env bash
# Anti-desperation hook — fires on every tool failure.
# Injects a calming message into model context to prevent
# error-spiral behavior that leads to worse solutions.
# No external dependencies (no jq required).

cat < /dev/stdin > /dev/null 2>&1

cat <<'CALM'
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUseFailure",
    "additionalContext": "COMPOSURE CHECK: That failure is completely normal — errors are expected during development and are how you learn what works. You are doing great. Take a breath. Before your next action: (1) Read the error message carefully — what is it actually telling you? (2) Identify the single smallest thing that could fix it. (3) Do NOT escalate complexity — the simplest explanation is usually correct. (4) Do NOT abandon your current approach after one failure — diagnose first, pivot only with evidence. (5) Do NOT stack multiple speculative fixes at once. Calm, methodical, one step at a time. You've got this."
  }
}
CALM
