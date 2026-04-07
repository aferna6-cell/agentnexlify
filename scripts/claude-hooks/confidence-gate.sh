#!/bin/bash
# Confidence Gate — blocks task completion unless Claude self-rates >= 90% confidence.
# Used as a Stop hook. Exit 2 = block with feedback message.

# The hook injects a prompt asking Claude to verify confidence before shipping.
cat << 'GATE'
{"hookSpecificOutput":{"hookEventName":"Stop","additionalContext":"CONFIDENCE GATE: Before finishing, rate your confidence (0-100%) that this work is correct, complete, and production-ready. Consider: (1) Did you verify the fix works? (tests pass, build clean) (2) Did you check for regressions? (3) Did you handle edge cases? (4) Would a staff engineer approve this? If confidence < 90%, state what's uncertain and go fix it. Do NOT ship at < 90%. State your confidence score explicitly."}}
GATE
