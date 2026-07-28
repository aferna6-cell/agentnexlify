# Idea 2 — Step 9G CORRECTION: CCR Routine Health Monitor

**Category:** Operational resilience  
**Evidence strength:** HIGH — GH #403 2026-07-23 comment confirms CCR deployed; KB 5 days since last update despite "twice daily" claim  
**Execution channel:** nightly SKILL.md bash block (same channel as Step 9F)

## What

The original Step 9G (run 100 winner) is OBSOLETE. It was designed to `gh workflow run kb-autopopulate.yml` when KB stale > 7 days. But:
1. GH Actions broken repo-wide (#500) — running the workflow would fail
2. CCR Routine ("KB Auto-Populate (CCR)") deployed 2026-07-23, handles KB autopopulate via cloud Routine (no Actions secret needed)

Implementing original Step 9G would produce incorrect diagnostic: "Check ANTHROPIC_API_KEY" when that's not the actual failure path anymore.

**The corrected Step 9G** verifies the CCR Routine is still running by checking for a recent KB-related PR:

```bash
# Step 9G: CCR Routine health check
RECENT_KB_PR=$(gh pr list -R aferna6-cell/agentnexlify \
  --search "kb autopopulate OR kb-autopopulate" \
  --state all --limit 5 \
  --json number,createdAt,title 2>/dev/null | \
  python3 -c "import json,sys; prs=json.load(sys.stdin); \
  from datetime import datetime,timezone; \
  now=datetime.now(timezone.utc); \
  recent=[p for p in prs if (now-datetime.fromisoformat(p['createdAt'])).days<=2]; \
  print(len(recent))")

if [ "$RECENT_KB_PR" = "0" ] && [ "$DAYS_STALE" -gt 7 ]; then
  gh issue comment 403 -R aferna6-cell/agentnexlify \
    --body "Step 9G (CCR monitor): KB stale ${DAYS_STALE} days AND no KB PR in last 48h. CCR Routine ('KB Auto-Populate (CCR)') may be stalled. Check: (1) cloud.claude.ai for Routine status (2) Last PR opened by claude.ai account (3) Whether subscription auth is valid."
fi
```

## Why it matters

This is a new silent-green failure class: the CCR Routine could stop without producing any observable difference (no error in GH Actions, no notification, KB just stops updating). Same failure class as Keys Koffee widget (5+ weeks undetected) and the 63-day KB gap.

The nightly SKILL.md already has Step 9F (staleness alert) but Step 9F doesn't distinguish "CCR Routine ran but didn't produce anything new" from "CCR Routine stopped entirely." Step 9G corrected fills this gap.

## Governance note

This requires updating governance.json to mark original Step 9G (run 100 winner) as "obsolete — CCR Routine deployed 2026-07-23, GH Actions #500 broken" and tracking this corrected version as the new recommendation.
