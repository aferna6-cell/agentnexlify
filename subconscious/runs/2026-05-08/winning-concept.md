# Winning Concept — 2026-05-08 (Run 15)

## Recommendation
Create `scripts/check-widget-sync.sh` to diff all 3 widget copies, wire it into the pre-push hook, and fix the stale CLAUDE.md Invariant #4 (says "2 copies", should say "3 copies").

## Why This, Why Now

**Moratorium re-triggered.** pending_approvals = 4 (runs 4, 7, 8, 14) > threshold = 3. Oldest pending = run 4 at 22 days, exceeding max_pending_age_days = 14. The repo has been quiet for 3 consecutive days with zero implementation. Moratorium mode re-activates to clear the backlog before new ideas are added.

**S-effort clears the deadlock.** Run 4 (AI-to-Human Handoff v1, M-effort) has been pending 22 days. Re-recommending M-effort items into a zero-velocity period doesn't move them. The faster path to exiting moratorium is implementing the 3 S-effort items in the pending queue (runs 7, 8, 14) — which together take ~1 hour — dropping pending from 4→1 and fully exiting moratorium.

**Widget divergence is a live production risk.** Three confirmed widget copies: `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`. Any commit that modifies `widget/` without syncing the other two silently breaks embeds on tenant sites. CLAUDE.md Invariant #4 says "2 copies" — this has been stale since the landing-page-v2 copy was identified in run 7 (14 days ago) and causes confusion when following the invariant.

**14 days unimplemented.** Run 7 was recommended on 2026-04-24. The implementation sketch is complete. No blockers have ever existed. It simply hasn't been done.

## Implementation Sketch

### Step 1: Create `scripts/check-widget-sync.sh`
```bash
#!/usr/bin/env bash
# Fails if any of the 3 widget copies diverge from the canonical source
set -euo pipefail

CANONICAL="widget/agentnexlify-widget.js"
COPIES=(
  "frontend/public/widget/agentnexlify-widget.js"
  "landing-page-v2/widget/agentnexlify-widget.js"
)

ERRORS=0
for COPY in "${COPIES[@]}"; do
  if [ ! -f "$COPY" ]; then
    echo "MISSING: $COPY"
    ERRORS=$((ERRORS + 1))
  elif ! diff -q "$CANONICAL" "$COPY" > /dev/null 2>&1; then
    echo "DIVERGED: $COPY differs from $CANONICAL"
    ERRORS=$((ERRORS + 1))
  fi
done

if [ $ERRORS -eq 0 ]; then
  echo "OK: all 3 widget copies are byte-identical"
  exit 0
else
  echo "BLOCKED: $ERRORS widget copy/copies out of sync — run: cp $CANONICAL <copy-path>"
  exit 1
fi
```

Make executable: `chmod +x scripts/check-widget-sync.sh`

### Step 2: Wire into `scripts/hooks/pre-push`
Add after the schema consistency check block:
```bash
# Widget sync check
echo -n "Widget sync... "
if bash scripts/check-widget-sync.sh > /dev/null 2>&1; then
  echo -e "${GREEN}OK${NC}"
else
  echo -e "${RED}BLOCKED${NC}"
  bash scripts/check-widget-sync.sh
  ERRORS=$((ERRORS + 1))
fi
```

### Step 3: Fix CLAUDE.md Invariant #4
Change:
```
**Widget JS byte-identical** in `widget/` AND `frontend/public/widget/` — mismatched copies break embeds on tenant sites.
```
To:
```
**Widget JS byte-identical** in `widget/`, `frontend/public/widget/`, AND `landing-page-v2/widget/` — mismatched copies break embeds on tenant sites.
```

### Step 4: Verify
```bash
bash scripts/check-widget-sync.sh  # should print OK
# Stage a change to one widget copy only
git add widget/agentnexlify-widget.js
git push  # should be BLOCKED by hook
```

---

## Bonus Steps (do these in same sitting — 45 additional minutes)

**Bonus A: Wire check_project_invariants.py (run 8, 13 days pending, 5 minutes)**

Add to `scripts/hooks/pre-commit` after the Check 9 block:
```bash
# Check 10: Project invariants (client_id, status, areas_of_interest, etc.)
echo -n "Check 10: Project invariants... "
if python3 scripts/check_project_invariants.py > /dev/null 2>&1; then
  echo -e "${GREEN}OK${NC}"
else
  echo -e "${RED}BLOCKED${NC}"
  python3 scripts/check_project_invariants.py
  ERRORS=$((ERRORS + 1))
fi
```
Closes run 8. pending 4→3.

**Bonus B: Wire lead qualifier golden eval to CI (run 14, 3 days pending, 20 minutes)**

Create `.github/workflows/lead-qualifier-eval.yml`:
```yaml
name: Lead Qualifier Golden Eval
on:
  schedule:
    - cron: '0 9 * * 1'  # Monday 9 AM UTC
  workflow_dispatch:

jobs:
  lead-qualifier-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - name: Skip if no secret
        if: ${{ env.LEAD_QUALIFIER_AGENT_ID == '' }}
        run: echo "LEAD_QUALIFIER_AGENT_ID not set — skipping eval" && exit 0
      - name: Run golden eval
        run: cd backend && python -m pytest tests/evals/test_lead_qualifier_golden.py -v --tb=short
        env:
          LEAD_QUALIFIER_AGENT_ID: ${{ secrets.LEAD_QUALIFIER_AGENT_ID }}
```
Add `LEAD_QUALIFIER_AGENT_ID` to GitHub Secrets. Closes run 14 + Issue #110. pending 4→2 (after bonus A) → 1.

**After implementing all 3:** pending = 1 (run 4 only). Moratorium fully exits. Queue healthy.

---

## What This Replaces
Run 7's Widget 3-Copy Sync Guard has been the pending winner since 2026-04-24. Moratorium re-triggered this run (pending = 4 > threshold = 3). This is a moratorium-mode recommendation.

## Moratorium Status After Implementation
- Before: pending = 4, moratorium re-triggered
- After run 7 only: pending = 3, moratorium boundary
- After runs 7 + 8: pending = 2, moratorium exits
- After runs 7 + 8 + 14: pending = 1, moratorium fully exited
- Remaining: run 4 (AI-to-Human Handoff v1) — oldest, M-effort, should be next sprint priority

## Escalation Note: Run 4 (AI-to-Human Handoff v1)
22 days pending. Cannot be auto-implemented. Requires deliberate sprint allocation. After S-effort items clear the queue, this should be the ONLY remaining item. No new subconscious winners should be accepted until run 4 is implemented or explicitly rejected.

## Confidence
**HIGH** — Evidence: (1) S-effort, no blockers, implementation sketch complete in run 7; (2) moratorium re-triggered by objective thresholds (4 > 3, 22 days > 14); (3) repo quiet 3 days = zero velocity, implementation nudge needed; (4) CLAUDE.md Invariant #4 stale fact documented 7+ runs; (5) widget production risk concrete (tenant embed breakage); (6) bonus steps for runs 8 + 14 require 45 additional minutes, drop pending from 4→1.
