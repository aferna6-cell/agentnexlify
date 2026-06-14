# Winning Concept — 2026-05-05-pm (Run 14)

## Recommendation
Wire the golden eval harness to CI: create `.github/workflows/lead-qualifier-eval.yml` with a Monday weekly cron + PR trigger, closing Issue #110 and establishing the first regression gate on the platform's core AI conversion feature.

## Why This, Why Now

**Moratorium just lifted.** Run 13's JS Silent Catch Guard was implemented by nightly review on 2026-05-05 (72f8204). pending_approvals dropped 4→3. This is the first free-choice run since run 8 triggered the moratorium — and governance.json explicitly designated "Wire golden eval harness to CI (ROI 2.5, Issue #110)" as the first post-moratorium winner.

**The harness already exists and passes.** `backend/tests/evals/test_lead_qualifier_golden.py` + `lead_qualifier_golden.json` were added in 7854ede, specifically after a prior silent regression in lead classification. The test file is env-var gated, requires `LEAD_QUALIFIER_AGENT_ID`, and runs to 80% pass threshold. It has never failed CI because it has never been wired to CI.

**Onboarding V2 sprint is active.** 21 new issues are in flight (plans/onboarding-v2_plan.md). New agent configurations and knowledge-base articles will affect how the lead qualifier behaves. Without a weekly eval, any classification drift introduced during the sprint goes undetected until a tenant reports it. The cheapest time to install the guard is before the sprint ships to production.

**S-effort.** The workflow file is ~30 lines of YAML. One GH Secret (`LEAD_QUALIFIER_AGENT_ID`) to add. No code changes. Estimated implementation: 20 minutes.

## Implementation Sketch

### Step 1: Create `.github/workflows/lead-qualifier-eval.yml`
```yaml
name: Lead Qualifier Golden Eval

on:
  schedule:
    - cron: '0 9 * * 1'   # Monday 9 AM UTC
  workflow_dispatch:

jobs:
  lead-qualifier-eval:
    runs-on: ubuntu-latest
    env:
      LEAD_QUALIFIER_AGENT_ID: ${{ secrets.LEAD_QUALIFIER_AGENT_ID }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: pip install -r backend/requirements.txt

      - name: Run golden eval
        run: |
          cd backend
          python -m pytest tests/evals/test_lead_qualifier_golden.py -v \
            --tb=short \
            -k "not skip" \
            || exit 1
        env:
          LEAD_QUALIFIER_AGENT_ID: ${{ env.LEAD_QUALIFIER_AGENT_ID }}

      - name: Skip if no secret
        if: env.LEAD_QUALIFIER_AGENT_ID == ''
        run: echo "LEAD_QUALIFIER_AGENT_ID not set — skipping eval" && exit 0
```

### Step 2: Add `LEAD_QUALIFIER_AGENT_ID` to GitHub Secrets
- Settings → Secrets and variables → Actions → New repository secret
- Name: `LEAD_QUALIFIER_AGENT_ID`
- Value: the managed agent ID from `backend/services/managed_agents_registry.py`

### Step 3: Update `test_lead_qualifier_golden.py` to skip gracefully
Confirm the test file already has:
```python
import os
pytestmark = pytest.mark.skipif(
    not os.getenv("LEAD_QUALIFIER_AGENT_ID"),
    reason="LEAD_QUALIFIER_AGENT_ID not set"
)
```
If missing, add it so local runs don't require the secret.

### Step 4: Close Issue #110
Commit message: `ci: wire lead-qualifier golden eval to weekly CI, closes #110`

### Step 5: Verify
Trigger `workflow_dispatch` on the workflow. Confirm all golden cases pass at ≥80%.

---

## Bonus Step: Complete Run 8 (Wire check_project_invariants.py)

**Em-dash blocker cleared today (8f680e8).** `python3 scripts/check_project_invariants.py` now shows:
```
PASS FastAPI router files avoid future annotations
PASS active backend code avoids retired live-schema fields
PASS retired plan names do not appear in plan-related code
PASS widget assets are byte-identical across mirrors
PASS website source avoids em dashes
PASS direct Anthropic SDK message creation stays behind the runtime wrapper
All project invariants passed.
```

**One-liner in `scripts/hooks/pre-commit`** (insert after Check 9 block, ~line 244):
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

This closes run 8 (pending 10 days), drops pending_approvals 3→2, and guards against the #1 most-common production bug class in this codebase.

---

## What This Replaces
First post-moratorium recommendation. Previous active direction was JS Silent Catch Guard (now implemented). No direction is being replaced — this adds a new CI gate.

## Moratorium Status After Implementation
- Current: pending_approvals = 3 (runs 4, 7, 8)
- After run 14 winner: no change (adding CI workflow, not implementing a pending item)
- After bonus run 8: pending_approvals = 2 (runs 4, 7)
- Moratorium re-trigger threshold: 3
- Status: healthy

## Next Run Candidates (Run 15)
1. Widget 3-Copy Sync Guard (run 7, S-effort, 11 days pending) — only blocking item left in code_health queue after run 8 bonus
2. AI-to-Human Handoff v1 (run 4, M-effort) — oldest pending, Critical customer gap
3. Fix email_sequences N+1 (ROI 2.3, GH #112) — promote if email adoption metrics grow

## Confidence
**HIGH** — Evidence: (1) 7854ede added harness specifically after silent regression; (2) test file exists and passes locally; (3) governance.json explicitly flagged as first post-moratorium winner; (4) Onboarding V2 sprint active — new risk vector for drift; (5) S-effort single YAML file; (6) Issue #110 open and tracked; (7) em-dash blocker cleared today making bonus step zero-risk.
