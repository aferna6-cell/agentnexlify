# Winning Concept — 2026-07-23-pm (Run 101)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml` and report the outcome (success or specific failure reason) to GH #403.

## Why This, Why Now
Step 9G is the 2nd carry-forward (runs 100 → 101). It was the run 100 winner and is absent from SKILL.md (grep returns 0 matches for "9G"). The mandate from governance fires when a winner is absent from the execution channel.

Step 9F fires correctly — nightly-2026-07-22 proves it: "Step 9F: KB STALE (9 days) — comment added to GH #403." But the alert does not trigger a fix. Today's KB update was a MANUAL CCR session workaround, NOT the automated workflow. The automated kb-autopopulate.yml workflow remains broken (ANTHROPIC_API_KEY + VOYAGE_API_KEY absent from GH Actions secrets). Step 9G surfaces that exact failure class with a specific diagnostic instead of continuing to alert humans who aren't watching GH #403.

The 63-day stale gap in early 2026 was caused by empty secrets with `continue-on-error: true` masking the failure silently. Step 9G closes that loop.

XS implementation in the proven autonomous channel (SKILL.md bash block, same class as Steps 9B-9F, all shipped in one cycle each).

## Implementation Sketch
- After the existing Step 9F staleness check block in SKILL.md, add a new `## Step 9G` bash block
- Condition: `DAYS_STALE -gt 7` (reuses the staleness variable Step 9F already computes)
- Action 1: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
- Action 2: `sleep 30`
- Action 3: `gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,createdAt,url` → parse conclusion
- If conclusion == "success": log "Step 9G: kb-autopopulate triggered — SUCCESS" and exit 0
- If conclusion == "failure" or "cancelled": comment on GH #403 with specific message: "Step 9G: kb-autopopulate.yml triggered but FAILED. Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions Secrets. Run URL: $RUN_URL"
- If conclusion still empty (run in progress after 30s): log "Step 9G: kb-autopopulate running — status check pending" and exit 0 (CI will complete on its own)
- Total new lines: ~30 bash, same template as Step 9F block

## What This Replaces
Step 9F's alert-only posture. Step 9F fires the human alarm; Step 9G attempts repair first and only escalates to human if secrets are invalid. Both steps coexist — Step 9G runs after Step 9F to preserve the audit trail.

## Run 101 Carry-Forward Notes
- KB updated manually today (2026-07-23 CCR session): 8 raw + 8 wiki articles, 124 total. Embeddings still skipped (VOYAGE_API_KEY missing).
- SHOW_BOOKING_PANEL (e9b4972) parked for run 102 investigation.
- email_sequences split (ab1a7c2) confirmed implemented; no registration gap found.
- MCP tenant count: 1 (281156f, 2026-07-23).

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps. `gh workflow run` uses `workflow_dispatch`; nightly already has write-side GH API permissions. Failure surface limited: silent failure is impossible (status check + comment on #403 catches it). Mandate fires (2nd carry-forward cycle).
