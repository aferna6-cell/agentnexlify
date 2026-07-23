# Winning Concept — 2026-07-23 (Run 100)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml` and report the outcome (success or specific failure reason) to GH #403.

## Why This, Why Now
Step 9F (run 99 winner) fires correctly — nightly-2026-07-22 proves it: "Step 9F: KB STALE (9 days) — comment added to GH #403." But the alert does not trigger a fix. The KB is now 10 days stale, and the 3 live tenants' AI chat quality depends on freshness (salon FAQ, vertical answers). The 63-day stale gap in early 2026 was caused by empty secrets with `continue-on-error: true` masking the failure silently — Step 9G surfaces that exact failure class with a specific diagnostic instead of continuing to alert humans who aren't watching the #403 issue. XS implementation in the proven autonomous channel (SKILL.md bash block, same class as Steps 9B-9F, all shipped in one cycle each).

## Implementation Sketch
- After the existing Step 9F staleness check block in SKILL.md, add a new `## Step 9G` bash block
- Condition: `DAYS_STALE -gt 7` (reuses the staleness variable Step 9F already computes)
- Action 1: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
- Action 2: `sleep 30`
- Action 3: `gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,createdAt,url` → parse conclusion
- If conclusion == "success": log "Step 9G: kb-autopopulate triggered — SUCCESS" and exit 0
- If conclusion == "failure" or "cancelled": comment on GH #403 with specific message: "Step 9G: kb-autopopulate.yml triggered but FAILED. Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions Secrets. Run URL: \$RUN_URL"
- If conclusion still empty (run in progress after 30s): log "Step 9G: kb-autopopulate running — status check pending" and exit 0 (CI will complete on its own)
- Total new lines: ~30 bash, same template as Step 9F block

## What This Replaces
Step 9F's alert-only posture. Step 9F fires the human alarm; Step 9G attempts repair first and only escalates to human if secrets are invalid. Both steps coexist — Step 9G runs after Step 9F to preserve the audit trail.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps. `gh workflow run` uses `workflow_dispatch`; nightly already has write-side GH API permissions (`gh issue comment`, `gh label add`, `gh run list`). Failure surface limited: silent failure is impossible (status check + comment on #403 catches it). Current stale window (10 days) makes this immediately load-bearing.
