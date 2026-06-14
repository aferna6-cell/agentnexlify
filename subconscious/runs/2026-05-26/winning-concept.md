# Winning Concept — 2026-05-26 (Run 34)

## Recommendation

Fix GH #181: add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py`, and update `backend/tests/test_billing_amount_to_plan.py` to replace the backwards issue-#81-era assertions with correct current-price assertions.

---

## Why This, Why Now

**Governance mandate fires.** Run 33 set an explicit 4-consecutive-run threshold for GH #181. This is run 34. The mandate mechanism is not advisory — it switches the winner regardless of competing ideas.

**CI is actively certifying a production bug as correct.** `test_no_wrong_15000_mapping` and `test_no_wrong_25000_mapping` (lines 38-44 of `test_billing_amount_to_plan.py`) assert that 15000 and 25000 should NOT exist in `AMOUNT_TO_PLAN`. These tests were written during issue #81 when wrong mappings existed. The issue was resolved but the tests weren't updated to reflect current pricing ($150/mo autopilot, $250/mo professional). Two failed fix attempts (c72b535, 1eaaeec) confirm that developers looking at this file are misled by the backwards tests. Any correct fix currently fails CI.

**Two consecutive autonomous implementations of run 33.** The nightly review executed both the god-class-splitter SKILL.md creation (e848b87) and SKILL.md Moratorium Escalation Protocol (2ce31b2) without human instruction. This confirms the autonomous path is working for LOW-risk additive changes. GH #181 is MEDIUM-risk billing code — it requires human action.

**S-effort, ~15 min.** Four targeted edits. No architecture. No migration. No new dependencies. The fix is a 15-minute task for a developer who has the precise locations.

---

## Implementation Sketch

### Step 1: Fix AMOUNT_TO_PLAN in billing.py

File: `backend/routers/billing.py`, line ~264

Current state (AMOUNT_TO_PLAN dict):
```python
AMOUNT_TO_PLAN: dict[int, str] = {
    9900: "growth",
    # ... legacy entries ...
    89900: "enterprise",
}
```

Add after `9900: "growth"`:
```python
    15000: "autopilot",   # $150/mo current price
    25000: "professional", # $250/mo current price
```

### Step 2: Fix test_billing_amount_to_plan.py

File: `backend/tests/test_billing_amount_to_plan.py`

**Remove** (lines 38-44):
```python
def test_no_wrong_15000_mapping(self):
    """Issue #81 claimed 15000->professional was present; verify it is NOT."""
    assert 15000 not in AMOUNT_TO_PLAN, "15000 should not be in AMOUNT_TO_PLAN"

def test_no_wrong_25000_mapping(self):
    """Issue #81 claimed 25000->enterprise was present; verify it is NOT."""
    assert 25000 not in AMOUNT_TO_PLAN, "25000 should not be in AMOUNT_TO_PLAN"
```

**Add** (new test methods):
```python
def test_current_autopilot_pricing_150(self):
    """$150/mo autopilot plan maps correctly."""
    assert AMOUNT_TO_PLAN.get(15000) == "autopilot"

def test_current_professional_pricing_250(self):
    """$250/mo professional plan maps correctly."""
    assert AMOUNT_TO_PLAN.get(25000) == "professional"
```

**Update** `test_all_four_current_tiers_present`:
```python
def test_all_four_current_tiers_present(self):
    """All four current Stripe price points are mapped."""
    assert {9900, 15000, 25000, 89900}.issubset(set(AMOUNT_TO_PLAN.keys()))
```

### Step 3: Run tests

```bash
cd backend && python -m pytest tests/test_billing_amount_to_plan.py -v
```

All methods should pass green.

### Step 4: Commit

```bash
git add backend/routers/billing.py backend/tests/test_billing_amount_to_plan.py
git commit -m "fix(billing): add 15000→autopilot + 25000→professional to AMOUNT_TO_PLAN

Closes GH #181. Two fix attempts (c72b535, 1eaaeec) both missed these
current-price entries. CI was certifying the broken state via backwards
issue-#81-era tests (test_no_wrong_15000_mapping, test_no_wrong_25000_mapping)
— replaced with positive current-price assertions. Governance mandate run 34."
```

---

## Standing Bonus Action: /moratorium-sprint

After GH #181 is fixed (~15 min), the human is already in implementation mode. The moratorium sprint is 3 additional S-effort items (~40 min):
- **Item A:** Wire `check_project_invariants.py` into `scripts/hooks/pre-commit` as Check 10 (~5 min, 3 lines)
- **Item B:** Create `scripts/check-widget-sync.sh` + wire into pre-push hook + fix CLAUDE.md Invariant #4 (~15 min)
- **Item D:** Create `.github/workflows/lead-qualifier-eval.yml` (~20 min)

Invoke `/moratorium-sprint` after GH #181. Sprint drops pending toward moratorium exit (≤2).

---

## What This Replaces

GH #181 was the runner-up in run 33 (behind god-class-splitter) with a governance escalation signal. Run 33's god-class-splitter winner was autonomously implemented this morning by nightly review (e848b87). GH #181 now has no competing priority from higher-ranking winners.

---

## Confidence

**HIGH** — Four independent evidence sources: (1) direct inspection of `billing.py:263-290` confirms 15000 and 25000 absent; (2) direct inspection of `test_billing_amount_to_plan.py:38-44` confirms backwards assertions; (3) two failed fix attempts (c72b535, 1eaaeec) in the commit log confirm the non-obvious nature that makes a precise sketch valuable; (4) governance mandate fires unconditionally at 4-consecutive-run threshold per governance.json rules. Debate: Idea 1 SURVIVES 3 rounds; /moratorium-sprint WEAKENED; email_sequences split WEAKENED.
