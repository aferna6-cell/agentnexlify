# Idea 1 — Step 9E Threshold Fix (2nd Carry-Forward)

**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Carry-forward count:** 2 (2nd carry from runs 119→120→121)
**Escalation status:** 3rd carry (run 122) = autonomous-executable

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` fires at `days_since_rotation >= 76`.
The `days_remaining <= 10` early-warning threshold from run 120 is NOT present (grep confirmed).

Today: AUTOPILOT_GH_TOKEN at 75 days since rotation. Threshold fires tomorrow. Expires 2026-10-02.
That is 15 days away. If token not rotated: autonomous loop dies.

Evidence (from today's nightly — 2026-09-17.md):
- AUTOPILOT_GH_TOKEN: 75d since rotation, threshold 76d, expires 2026-10-02
- Step 9E fires at 76d but does NOT have the 10-day window escalation

## Implementation

Single edit in `.claude/skills/nightly-commit-review/SKILL.md`, Step 9E block.

Change from:
```
if days_since_rotation >= 76:
    log_warning + comment on GH
```

Change to:
```
days_remaining = 90 - days_since_rotation  # 90d rotation interval
if days_since_rotation >= 76 OR days_remaining <= 10:
    # Existing GH issue search + comment/create logic
    # Add days_remaining to comment body
```

The GH issue search/dedup mechanism already exists (implemented in earlier run).
Only the threshold logic and days_remaining calculation need adding.

## Expected outcome

- Step 9E fires today (75d ≥ 76 threshold is 1 day away — but days_remaining = 15 ≤ 10 would fire now)
- GH #399 receives a comment with urgency: "15 days remaining, rotate by 2026-10-02"
- Owner gets email notification via GH subscription
- If not rotated in 15 days, loop dies
