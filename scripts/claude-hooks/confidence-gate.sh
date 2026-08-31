#!/bin/bash
# Confidence Gate — blocks the FIRST stop to force self-assessment.
# Second stop (after Claude self-assessed) passes through.
# Uses a fixed flag file to track across hook invocations.

# Drain stdin
cat < /dev/stdin > /dev/null 2>&1

FLAG="/tmp/.claude-confidence-gate"

# If flag exists and is recent (< 5 min old), Claude already self-assessed — let it stop
if [ -f "$FLAG" ] && [ "$(find "$FLAG" -mmin -5 2>/dev/null)" ]; then
    rm -f "$FLAG"
    exit 0
fi

# First stop — create flag and block with confidence prompt
touch "$FLAG"

cat << 'GATE'
{"decision":"block","reason":"CONFIDENCE GATE: Before finishing, rate your confidence (0-100%) that this work is correct, complete, and production-ready. Consider: (1) Did you verify the fix works? (tests pass, build clean) (2) Did you check for regressions? (3) Did you handle edge cases? (4) Would a staff engineer approve this? If confidence >= 90%, state your score and finish. If < 90% and the gap is agent-fixable, state what's uncertain and keep working. If < 90% solely due to a human/external blocker already reported (OAuth consent, secrets, dashboard clicks), follow .claude/rules/confidence-gate-escape.md: report HOLD with score, Verified line, and stop — do NOT remint/poll/busy-loop."}
GATE
