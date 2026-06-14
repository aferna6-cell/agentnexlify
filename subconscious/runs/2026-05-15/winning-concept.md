# Winning Concept — 2026-05-15 (Run 17)

## Recommendation
Create `scripts/check-widget-sync.sh`, wire it into the pre-push hook, and fix CLAUDE.md Invariant #4 — the same S-effort recommendation made in runs 15 and 16, now 21 days from the original recommendation and still unimplemented.

## Why This, Why Now

**Moratorium still active.** pending_approvals = 4 (runs 4, 7, 8, 14) > threshold = 3. Run 4 at 29 days (was 25 in run 16). Zero commits implementing any pending item in 4 days since run 16. Three nightly reviews (May 13-15) confirm no code activity.

**Moratorium protocol: oldest S-effort pending wins.** Run 7 (Widget 3-Copy Sync Guard, April 24) is day 21 — the oldest S-effort pending item. No blockers have ever existed. Implementation sketch is complete and unchanged since run 15. Widget copies are in sync today (confirmed May 15), which means the guard is preventative: it protects future state, not current state. Any widget edit without the guard can silently diverge.

**JS Silent Catch precedent validates persistence.** JS Silent Catch was recommended across 5 consecutive moratorium runs (9-13, April 27 → May 4) before being implemented on May 5. We are at run 3 with Widget Sync Guard (runs 15, 16, 17). The precedent says the mechanism works — it requires sustained pressure.

**Run 18 boundary condition:** If Widget 3-Copy Sync Guard is STILL unimplemented when run 18 executes, the "4 consecutive moratorium runs with same winner" threshold (per run 16 governance guidance) will be reached. Run 18 must switch winner to the Automated Moratorium Escalation Hook — modify `nightly-commit-review.sh` to auto-create GH comments on oldest pending issues when moratorium is active. This transition is mandatory at run 18 if implementation has not occurred.

**One-sitting path from pending=4 → pending=1:**
- Bonus A: Wire `check_project_invariants.py` into pre-commit (run 8, ~5 min, drops pending 4→3)
- Bonus B: Wire lead qualifier golden eval to CI (run 14, ~20 min, drops pending 3→2)
- Winner (run 7): Create widget sync guard (run 7, ~15 min, drops pending 2→1)
- Total: ~40 minutes. Run 4 (AI-to-Human Handoff, M-effort) remains as the only pending item, requiring deliberate sprint.

## Implementation Sketch

*Implementation sketch carried forward from run 15/16 winning-concept.md. No changes required — zero blockers confirmed.*

### Step 1: Create `scripts/check-widget-sync.sh` (~5 min)
```bash
#!/usr/bin/env bash
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

### Step 2: Wire into `scripts/hooks/pre-push` (~5 min)
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

### Step 3: Fix CLAUDE.md Invariant #4 (~2 min)
Change:
> **Widget JS byte-identical** in `widget/` AND `frontend/public/widget/` — mismatched copies break embeds on tenant sites.

To:
> **Widget JS byte-identical** in `widget/`, `frontend/public/widget/`, AND `landing-page-v2/widget/` — mismatched copies break embeds on tenant sites.

### Step 4: Verify (~3 min)
```bash
bash scripts/check-widget-sync.sh  # should print: OK: all 3 widget copies are byte-identical
```

---

## Bonus Steps (same sitting — 25 additional minutes, drops pending 4→1)

**Bonus A: Wire check_project_invariants.py (run 8, day 20, ~5 min)**

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
Script passes all 6 checks (confirmed May 15). Closes run 8. pending 4→3.

**Bonus B: Wire lead qualifier golden eval to CI (run 14, day 10, ~20 min)**

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
Add `LEAD_QUALIFIER_AGENT_ID` to GitHub Secrets. Closes run 14 + Issue #110. pending 3→2 → 1.

---

## After Moratorium Exits

Once pending = 1 (only run 4 remains):
1. **Zapier API key plan_status enforcement** (issue #107, 15+ days open, HIGH security) — route via issue-to-pr-loop. Add `plan_status IN ('active','trialing')` filter in `backend/services/zapier_auth.py::_get_api_key_client`. Regression test for cancelled tenant auth.
2. **AI-to-Human Handoff v1** (run 4, 29 days pending) — explicit-trigger-only, M-effort, 1.5-2 days. Requires deliberate sprint allocation.

## Run 18 Mandate (IF STILL UNIMPLEMENTED)

This is the explicit escalation boundary set by this run:

> If Widget 3-Copy Sync Guard is STILL unimplemented when run 18 executes, run 18 MUST switch its winner to the **Automated Moratorium Escalation Hook**: modify `scripts/daily/nightly-commit-review.sh` to auto-create a GH comment on the oldest pending issue (linking `winning-concept.md`) when moratorium is active AND oldest_pending_age > 14 days. This closes the recommendation→implementation feedback gap by creating automated pressure in GitHub, where humans spend implementation time.

> At 4 consecutive moratorium runs with the same winner, the system mechanism is worth questioning (per run 16 governance). Run 18 is that boundary.

## What This Replaces
Run 16's Widget 3-Copy Sync Guard recommendation (2026-05-11). Same winner, 4 days older.

## Moratorium Status After Implementation
- Before: pending = 4, moratorium active
- After run 7 only: pending = 3, moratorium boundary
- After runs 7 + 8: pending = 2, moratorium exits
- After runs 7 + 8 + 14: pending = 1, moratorium fully exited (run 4 is only remaining — requires sprint)

## Confidence
**HIGH** — Evidence: (1) S-effort, zero blockers confirmed May 15; (2) moratorium mandate (pending=4 > 3, 29 days > 14); (3) implementation sketch unchanged and complete since run 15; (4) JS Silent Catch precedent (5 moratorium runs before implementation) validates persistence mechanism; (5) widget copies confirmed in sync today — guard is preventative, not reactive; (6) Bonus A+B drop pending 4→1 in one 45-minute sitting; (7) run 18 escalation boundary explicitly set to maintain pressure regardless of outcome.
