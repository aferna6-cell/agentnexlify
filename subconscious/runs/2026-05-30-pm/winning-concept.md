# Winning Concept — 2026-05-30-pm (Run 42)

## Recommendation

Fix GH #181 (~15 min) then invoke `/god-class-splitter` on `backend/routers/email_sequences.py` (~2h) — human present in interactive session NOW is the forcing function.

---

## Why This, Why Now

Prerequisites for the email_sequences split were cleared just 24 hours ago by d481799 (nightly 2026-05-30). Run 41 was the first recommendation after unblocking; run 42 is the first human-present evening session since that unblocking. The distinction from run 41 is execution context: the user is actively running `/subconscious` interactively — the same forcing-function pattern that made run 22's "5-minute human-present" recommendation actionable. Today's nightly review autonomously created GH #193 (moratorium escalation, 44 days oldest, 13 pending) — the system is signaling its own urgency externally. The implementation sketch is fully written in run 41's winning-concept.md. The two prerequisite skills (god-class-splitter, post-split-test-repair) are confirmed in `.claude/skills/`. No setup cost; direct execution is possible this session.

---

## Implementation Sketch

### Step 0 — Prerequisite verification (30 seconds)
```bash
wc -l backend/routers/email_sequences.py       # confirm 1255L
ls .claude/skills/god-class-splitter/SKILL.md  # confirm exists (e848b87)
ls .claude/skills/post-split-test-repair/SKILL.md  # confirm exists (d481799)
```

### Step 1 — Fix GH #181 FIRST (~15 min, human required)
```python
# backend/routers/billing.py:263 — AMOUNT_TO_PLAN dict
# ADD after line for 9900:
15000: "autopilot",
25000: "professional",
```
```python
# backend/tests/test_billing_amount_to_plan.py
# REMOVE lines 38-44 (test_no_wrong_15000_mapping + test_no_wrong_25000_mapping)
# ADD two replacement methods:
def test_current_15000_maps_to_autopilot(self):
    assert AMOUNT_TO_PLAN[15000] == "autopilot"
def test_current_25000_maps_to_professional(self):
    assert AMOUNT_TO_PLAN[25000] == "professional"
# UPDATE test_all_four_current_tiers_present to assert {9900, 15000, 25000, 89900}
```
After fix: Check 11 stops firing WARNING. CI green for billing tests.

### Step 2 — Invoke /god-class-splitter (~2h)
```
/god-class-splitter
```
Supply target: `backend/routers/email_sequences.py`

The skill identifies 3 clean concerns:
- **email_crud.py** — sequence CRUD (create/read/update/delete sequences + templates)
- **email_enrollment.py** — lead enrollment, unenrollment, status tracking
- **email_processor.py** — `_process_pending_sends`, `run_sequence_processor`, scheduling

### Step 3 — Run /post-split-test-repair immediately after (~20 min)
```
/post-split-test-repair
```
8-step checklist:
1. `grep -rn "from backend.routers.email_sequences import" backend/tests/` — find stale imports
2. Repoint `@patch("backend.routers.email_sequences.*")` targets to new module paths
3. Fix ImportError in any affected test files
4. `python -m pytest backend/tests/ -x -q` — must pass
5. Verify no 500 errors in Railway logs for email sequence endpoints

### Step 4 — Commit and update GH issues
```bash
git add backend/routers/email_crud.py backend/routers/email_enrollment.py \
        backend/routers/email_processor.py backend/main.py backend/tests/
git commit -m "refactor(email): split email_sequences.py (1255L) → crud+enrollment+processor"
```
Update GH #112 + #113 labels: add new module names (email_processor.py for N+1 fix scope).

---

## Parking Lot Bonus Actions (for nightly or alongside)

**Item A spec (check_project_invariants pre-commit) — potential nightly pickup:**
Add to `scripts/hooks/pre-commit` after Check 11 block:
```bash
# Check 12: Project invariants (naming conventions)
echo -n "Check 12: Project invariants... "
if python scripts/check_project_invariants.py > /tmp/invariants_out 2>&1; then
    echo "PASS"
else
    cat /tmp/invariants_out
    exit 1
fi
```
This is AUTONOMOUS-EXECUTABLE if nightly-commit-review SKILL.md extends scope to pre-commit check additions.
Evidence: 061582c added Check 11 (22 lines) autonomously. Item A is 9 lines calling existing script.

**Item D spec (lead-qualifier-eval.yml) — human execution:**
Create `.github/workflows/lead-qualifier-eval.yml`:
```yaml
name: Lead Qualifier Eval
on:
  schedule:
    - cron: '0 9 * * 1'  # Monday 9 AM
  pull_request:
    paths:
      - 'backend/services/lead_qualifier.py'
      - 'backend/tests/evals/**'
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: python -m pytest backend/tests/evals/test_lead_qualifier_golden.py -v
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LEAD_QUALIFIER_AGENT_ID: ${{ secrets.LEAD_QUALIFIER_AGENT_ID }}
```
Closes GH #110. Item D of moratorium sprint.

---

## What This Replaces

Run 41 active_direction ("email_sequences split, all prerequisites met"). Run 42 adds the GH #181
prerequisite explicitly and the human-present forcing-function framing. Run 41's implementation
sketch is valid and referenced — run 42 adds GH #181 as explicit Step 1.

---

## Confidence

**MEDIUM** — same as run 41. All tooling prerequisites met (HIGH evidence). Risk: first production
use of god-class-splitter on complex file with enrollment/billing-adjacent logic. GH #181 fix is
MEDIUM risk (billing code + test mutation). Confidence raises to HIGH if GH #181 fix is confirmed
clean before starting split.
