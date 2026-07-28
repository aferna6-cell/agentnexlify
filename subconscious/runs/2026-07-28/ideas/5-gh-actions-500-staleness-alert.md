# Idea 5 — GH Actions #500 Staleness Alert (Nightly Step 9H)

**Category:** Operational resilience  
**Evidence strength:** MEDIUM — GH #403 2026-07-23 comment mentions "#500 Actions currently failing repo-wide"  
**Execution channel:** nightly SKILL.md bash block

## What

Add a nightly check: if GH Actions has had no successful workflow run in 72h, comment on #500 with a staleness diagnostic.

```bash
# Step 9H: GH Actions health check
LAST_SUCCESS=$(gh run list -R aferna6-cell/agentnexlify \
  --status success --limit 1 \
  --json createdAt 2>/dev/null | \
  python3 -c "import json,sys; runs=json.load(sys.stdin); print(runs[0]['createdAt'][:10] if runs else 'never')")

DAYS_SINCE=$(python3 -c "
from datetime import datetime,timezone
last=datetime.fromisoformat('${LAST_SUCCESS}T00:00:00+00:00') if '${LAST_SUCCESS}' != 'never' else None
now=datetime.now(timezone.utc)
print((now-last).days if last else 999)")

if [ "$DAYS_SINCE" -gt 3 ]; then
  gh issue comment 500 -R aferna6-cell/agentnexlify \
    --body "GH Actions staleness (day ${DAYS_SINCE}): no successful workflow run in ${DAYS_SINCE} days. Effects: (1) autopilot-issue-loop stalled (2) kb-autopopulate.yml broken (3) PR CI not running. CCR Routine workaround active for KB. Fix: check Actions tab for root cause."
fi
```

## Why it matters

GH Actions broken repo-wide (#500) means:
- autopilot-issue-loop stalled (40+ ai-ready issues queued per GH #403 comments)
- `kb-autopopulate.yml` broken (now worked around by CCR Routine)
- CI not running on PRs (nightly noted this in the context of the FastAPI bump testing)

Each day of silence on #500 is a day of unprocessed issues and unvalidated PRs. A recurring nightly reminder keeps the owner aware without manual monitoring.

## Weakness

GH Actions #500 is already an open issue — the owner knows about it. A recurring comment every day would be noisy and might mask signal with noise. The nightly could instead post at 72h, 7d, 14d, 30d intervals (exponential backoff on alerts). But that requires state tracking.

This idea is lower priority than the others because:
1. The issue is already known and tracked in GH #500
2. The key downstream effect (KB autopopulate) is already worked around
3. Autopilot loop being stalled has a separate root cause (GH #399 AUTOPILOT_GH_TOKEN)

Better framed as a secondary check inside idea 2's Step 9G corrected implementation.
