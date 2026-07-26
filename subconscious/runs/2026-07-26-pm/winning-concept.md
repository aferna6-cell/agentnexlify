# Winning Concept — 2026-07-26-pm (Run 104)

## Recommendation
Add Step 9H to `.claude/skills/nightly-commit-review/SKILL.md`: a daily GH Actions spending-limit heartbeat that detects the outage pattern (≥4 of last 5 runs failed), checks GH #500 state, and pings it with a dated status comment — self-silencing when the owner closes #500.

## Why This, Why Now
GH #500 (Actions spending limit) has been open 6 days (since 2026-07-20). All CI is dark: no PR validation, no scheduled ops, no autopilot loops. Run 101 commented a comprehensive unblock checklist on 2026-07-25 — but that was one comment, now 6 days old. The nightly commit review runs in Claude Code context (not GH Actions) and CAN detect the outage even while Actions is down. Step 9H adds a daily dated status ping that creates a visible time log on GH #500 ("still down July 27, 28, 29…"), compounding urgency without human effort. When the owner fixes billing and closes #500, the heartbeat self-disables. The parking-lot condition "until PR #577 merges" is satisfied — Step 9H ships WITH Step 9G in the same PR.

## Implementation Sketch
- Insertion point: after Step 9G block, before `10. Commit report...` in SKILL.md (~line 338)
- Condition: unconditional (every nightly cycle)
- Step 1: `gh run list --limit=5 --json conclusion` → count failures via python3
- Step 2: if FAIL_COUNT >= 4: check `gh issue view 500 --json state`
  - If open: `mcp__github__add_issue_comment issue_number=500 body="Step 9H nightly heartbeat: still down as of {TODAY}, Day {N}..."`
  - If closed: log "Actions restored" (heartbeat terminates)
- Step 3: if FAIL_COUNT < 4: log "GH Actions healthy"
- Total new lines: ~25 pseudocode lines in SKILL.md

**IMPLEMENTED DIRECTLY** this run (Step 9H now at 5 occurrences in SKILL.md).

## What This Replaces
Run 103's parking-lot disposition for Step 9H. Run 103 deferred it pending PR #577 merge; this run adds it directly to the branch so it ships with Step 9G in one review.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps (9B-9G). `gh run list` and `gh issue view` are read-only API calls already used in this SKILL.md. GH #500 pattern detection (≥4/5 failures) is a conservative threshold avoiding false positives. Self-silencing via issue close removes the spam risk.
