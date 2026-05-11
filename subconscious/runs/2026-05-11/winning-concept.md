# Winning Concept — 2026-05-11 (Run 16)

## Recommendation
Create `scripts/check-widget-sync.sh`, wire it into the pre-push hook, and fix CLAUDE.md Invariant #4 — the same S-effort recommendation made in run 15 (May 8), now 3 days older and still unimplemented.

## Why This, Why Now

**Moratorium still active.** pending_approvals = 4 (runs 4, 7, 8, 14) > threshold = 3. Run 4 at 25 days (was 22 in run 15). Zero commits implementing any pending item since the moratorium was re-triggered on May 8. Three days of nightly reviews (May 9-10) confirmed the moratorium status and flagged all 3 S-effort items as "ready for 1-hour sprint when human approves."

**Why the same winner again.** JS Silent Catch (run 3) was recommended across 6 consecutive moratorium runs (9-13) before being implemented. The mechanism is sustained pressure, not novelty. Switching to a new idea in run 16 would add a 5th pending item and move the exit condition further away. The moratorium protocol is working as designed — the bottleneck is human approval and execution, not idea quality.

**Widget sync guard is the right S-effort anchor.** Run 7 (April 24) identified 3 widget copies and the missing guard. Run 15 confirmed the implementation sketch and provided the complete script. The script is still MISSING on May 11. No blockers have ever existed. Both nightly reviews flagged this as "ready for 1-hour sprint."

**New context since run 15.** Zapier API key security bug (issue #107, 11 days open) is a newly confirmed security gap. It's tracked in GH already and should be the FIRST code fix addressed AFTER the moratorium exits — not before. The S-effort pending items must clear first.

## Implementation Sketch

*Full implementation sketch carried forward from run 15's winning-concept.md. No changes required.*

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
bash scripts/check-widget-sync.sh  # should print OK
```

---

## Bonus Steps (same sitting — 25 additional minutes, drops pending 4→1)

**Bonus A: Wire check_project_invariants.py (run 8, 16 days pending, ~5 min)**

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
Script currently PASSES all 6 checks (nightly reviews confirm). Closes run 8. pending 4→3.

**Bonus B: Wire lead qualifier golden eval to CI (run 14, 6 days pending, ~20 min)**

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

First priority once pending = 1 (run 4 only):

1. **Zapier API key plan_status enforcement** (issue #107, 11 days open) — add `plan_status IN ('active','trialing')` filter in `backend/services/zapier_auth.py::_get_api_key_client`. This is a code fix, NOT a subconscious recommendation — route via issue-to-pr-loop.
2. **AI-to-Human Handoff v1** (run 4, 25 days pending) — deliberate sprint allocation, 1.5-2 days. Cannot be auto-implemented.

## What This Replaces
Run 15's Widget 3-Copy Sync Guard recommendation (2026-05-08). Same winner, 3 days older.

## Moratorium Status After Implementation
- Before: pending = 4, moratorium active
- After run 7 only: pending = 3, moratorium boundary
- After runs 7 + 8: pending = 2, moratorium exits
- After runs 7 + 8 + 14: pending = 1, moratorium fully exited (run 4 is only remaining — requires sprint)

## Confidence
**HIGH** — Evidence: (1) S-effort, no blockers, implementation sketch complete since run 15; (2) moratorium mandate enforced by objective thresholds (pending=4 > 3, 25 days > 14); (3) zero implementation velocity over 3 days confirms human approval is the ONLY blocker; (4) JS Silent Catch precedent (6 moratorium runs before implementation) validates the persistence mechanism; (5) nightly reviews independently confirm moratorium and flag same items; (6) bonus steps for runs 8+14 require 25 additional minutes, drop pending from 4→1 in a single sitting.
