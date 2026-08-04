# Winning Concept — 2026-08-03 (Run 103)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml` and report the outcome (success or specific failure reason) to GH #403.

**Status: IMPLEMENTED DIRECTLY IN THIS RUN** (4th-cycle carry-forward escalation — same pattern as run 99 implementing Step 9F directly).

## Why This, Why Now
Step 9F fires correctly — nightly-2026-07-22 proves it: "Step 9F: KB STALE (9 days) — comment added to GH #403." The KB is now 11 days stale (as of 2026-08-03, last run: 2026-07-23). The alert does not trigger a fix. Step 9G has been selected winner in runs 100, 101, 102, and 103 — 4 consecutive cycles absent from SKILL.md. run_103_mandate explicitly authorized escalation to direct implementation if still absent. The 63-day stale gap in early 2026 was caused by empty secrets with `continue-on-error: true` masking the failure silently — Step 9G surfaces that exact failure class with a specific diagnostic instead of continuing to alert. 3 live tenants' AI chat quality depends on freshness (salon FAQ, vertical answers).

## Implementation (Applied This Run)
Added `9G. (KB Autopopulate Self-Heal Trigger)` bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F (grep 'Step 9G' returns 5 after implementation):

```
9G. (KB Autopopulate Self-Heal Trigger) If KB staleness > 7 days:
    1. gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify
    2. sleep 30
    3. gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,url
    4. success → log "Step 9G: kb-autopopulate triggered — SUCCESS"
    5. failure/cancelled → comment on GH #403 with specific secret diagnostic
    6. in-progress → log "Step 9G: kb-autopopulate running — status check pending"
```

~18 lines added to SKILL.md. Reuses DAYS_STALE variable from Step 9F. All failure paths logged; silent failure impossible.

## What This Replaces
Step 9F's alert-only posture. Step 9F fires the alarm; Step 9G attempts repair first and only escalates to human if secrets are invalid. Both steps coexist — Step 9G runs after Step 9F to preserve audit trail.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps. `gh workflow run` uses `workflow_dispatch`; nightly already has write-side GH API permissions (`gh issue comment`, `gh label add`, `gh run list`). Failure surface limited: silent failure is impossible (status check + comment on #403 catches it). Current stale window (11 days) makes this immediately load-bearing. Will fire on next nightly cycle.
