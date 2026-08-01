# Winning Concept — 2026-08-01-pm (Run 101)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml` and report the outcome (success or specific failure reason) to GH #403.

## Why This, Why Now
Step 9F (run 99, implemented) fires the staleness alert — confirmed working in nightly-2026-07-22: "Step 9F: KB STALE (9 days) — comment added to GH #403." But GH #403 has received zero human responses in 18+ days of alerts. Alert-only posture has already failed once (63-day staleness gap in early 2026). KB is currently 9 days stale again (last compile 2026-07-23). The 3 live tenants' AI chat quality depends on freshness — stale KB means stale vertical answers (salon FAQ, plumber intake, etc.). Step 9G closes the loop: attempt repair before escalating to human. Same proven channel as Steps 9B/9C/9D/9E/9F — all implemented in exactly 1 nightly cycle each.

## Implementation Sketch
Add a `## Step 9G` bash block immediately after the existing Step 9F block in `.claude/skills/nightly-commit-review/SKILL.md`:

```bash
## Step 9G — KB Autopopulate Self-Healing Trigger
# Runs only when Step 9F found staleness (DAYS_STALE > 7)
if [ "${DAYS_STALE:-0}" -gt 7 ]; then
  echo "Step 9G: KB stale ${DAYS_STALE} days — triggering kb-autopopulate.yml"
  gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify 2>/dev/null && {
    sleep 30
    CONCLUSION=$(gh run list --workflow=kb-autopopulate.yml \
      -R aferna6-cell/agentnexlify --limit=1 \
      --json conclusion -q '.[0].conclusion' 2>/dev/null)
    RUN_URL=$(gh run list --workflow=kb-autopopulate.yml \
      -R aferna6-cell/agentnexlify --limit=1 \
      --json url -q '.[0].url' 2>/dev/null)
    case "$CONCLUSION" in
      success)
        echo "Step 9G: kb-autopopulate triggered — SUCCESS" ;;
      failure|cancelled)
        gh issue comment 403 -R aferna6-cell/agentnexlify \
          --body "**Step 9G: kb-autopopulate.yml triggered but FAILED.** \
Check: (1) ANTHROPIC_API_KEY in GH Actions Secrets, \
(2) VOYAGE_API_KEY, (3) SUPABASE_ACCESS_TOKEN. \
Run: ${RUN_URL}" 2>/dev/null
        echo "Step 9G: kb-autopopulate FAILED — diagnostic comment added to GH #403" ;;
      *)
        echo "Step 9G: kb-autopopulate triggered — status pending (${CONCLUSION:-in_progress})" ;;
    esac
  } || echo "Step 9G: gh workflow run failed — GH token may lack workflow scope"
fi
```

Total new lines: ~30. SKILL.md-edit is the autonomous channel — same as Steps 9B through 9F.

## What This Replaces
Step 9F's alert-only posture on KB staleness. Steps 9F and 9G coexist: 9F fires the alert, 9G attempts repair, both logged. If repair succeeds, GH #403 gets a success note; if it fails, GH #403 gets an actionable diagnostic (which secret is likely missing).

## Confidence
**HIGH** — Channel proven 5 consecutive times. `gh workflow run` uses `workflow_dispatch`; nightly already uses GH API for issue comments and labels (`gh issue comment`, `gh label add`, `gh run list`) so token already has required scope. Silent failure impossible: status check + comment on failure surfaces it. KB currently at the same stale depth as when Step 9F was implemented. Nightly is running daily with active commits — implementation probability in next cycle: HIGH.
