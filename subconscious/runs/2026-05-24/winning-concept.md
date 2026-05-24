# Winning Concept — 2026-05-24 (Run 33)

## Recommendation

Fix GH #181 (third recommendation): add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py`, and remove the two CI-blocking test methods in `backend/tests/test_billing_amount_to_plan.py` that actively block any correct fix from turning CI green.

---

## Why This, Why Now

**The CI booby-trap is an active daily hazard.** Commit 1553bf7 (nightly review 2026-05-23) wired `test_billing_amount_to_plan.py` into CI. That file contains `test_no_wrong_15000_mapping` (line 38) and `test_no_wrong_25000_mapping` (line 42), which assert these keys MUST NOT exist. Any developer who adds the correct entries tomorrow sees CI go red and may revert — the docstring reinforces this by calling legacy prices "current pricing." The trap is not theoretical: commit 1eaaeec was titled "Fix billing AMOUNT_TO_PLAN" and STILL missed both entries, confirming the test file's framing is actively misleading.

**Three commits have missed the same entries.** c72b535, 1eaaeec, and 2174732 have all landed since GH #181 was filed without applying the fix. This is a non-obviousness signal — not negligence. The fix requires knowing BOTH (a) which entries are missing AND (b) that the test file's assertions are backwards. Only the subconscious brief connects both.

**S-effort, moratorium-safe, no migration, no new dependencies.** Two dict entries and four test method edits. ~15 min. Closes GH #181.

---

## Implementation Sketch

**Total estimated time: ~15 min**

### Step 1: Add missing entries to billing.py

File: `backend/routers/billing.py`, line ~263 (`AMOUNT_TO_PLAN` definition).

The `# Monthly only (current pricing)` block currently reads:
```python
# Monthly only (current pricing)
9900: "growth",
89900: "enterprise",
```

Add two entries:
```python
# Monthly only (current pricing)
9900: "growth",
15000: "autopilot",    # $150/mo current price — CLAUDE.md plan prices
25000: "professional", # $250/mo current price — CLAUDE.md plan prices
89900: "enterprise",
```

### Step 2: Fix contradictory tests in test_billing_amount_to_plan.py

**Remove** both of these methods (they are backwards after the issue #81 fix landed):
```python
def test_no_wrong_15000_mapping(self):  # line ~38 — DELETE
    ...
def test_no_wrong_25000_mapping(self):  # line ~42 — DELETE
    ...
```

**Add** two replacement methods:
```python
def test_current_autopilot_pricing_150(self):
    """$150/mo autopilot maps correctly (current price — CLAUDE.md, GH #181)."""
    assert AMOUNT_TO_PLAN[15000] == "autopilot"

def test_current_professional_pricing_250(self):
    """$250/mo professional maps correctly (current price — CLAUDE.md, GH #181)."""
    assert AMOUNT_TO_PLAN[25000] == "professional"
```

**Update** `test_all_four_current_tiers_present` (line ~56):
```python
def test_all_four_current_tiers_present(self):
    """All four current-price tiers must be present (CLAUDE.md plan prices)."""
    current_prices = {9900, 15000, 25000, 89900}  # $99, $150, $250, $899
    for amount in current_prices:
        assert amount in AMOUNT_TO_PLAN, f"${amount/100:.0f}/mo entry missing from AMOUNT_TO_PLAN"
```

**Update the file docstring** to note that legacy prices are preserved for existing subscribers and current prices are {9900, 15000, 25000, 89900}.

### Step 3: Verify

```bash
cd /home/user/agentnexlify
python -m pytest backend/tests/test_billing_amount_to_plan.py -v
```

All tests should pass. No test should assert that 15000 or 25000 are absent.

### Step 4: Commit

```
fix(billing): add current-price entries to AMOUNT_TO_PLAN, fix contradictory tests (GH #181)

15000 (autopilot, $150/mo) and 25000 (professional, $250/mo) absent from
AMOUNT_TO_PLAN. Three commits (c72b535, 1eaaeec, 2174732) missed these entries.
Tenants at current prices without metadata.plan resolve to None in _resolve_plan().

Removes test_no_wrong_15000_mapping + test_no_wrong_25000_mapping — correct for
issue #81 but now backwards and CI-blocking for any correct fix attempt. Updates
test_all_four_current_tiers_present to use actual current prices {9900,15000,25000,89900}.

Closes GH #181.
```

### Bonus Step A (~10 min): Pre-commit billing sentinel (Check 11)

After the fix lands, add to `scripts/hooks/pre-commit`:

```bash
# Check 11: Billing AMOUNT_TO_PLAN current-price sentinel
echo -n "Check 11: billing current-price entries present... "
python3 -c "
import sys
sys.path.insert(0, '.')
from backend.routers.billing import AMOUNT_TO_PLAN
required = {9900, 15000, 25000, 89900}
missing = required - set(AMOUNT_TO_PLAN.keys())
if missing:
    print('FAIL — missing entries: ' + str(missing))
    sys.exit(1)
" 2>/dev/null && echo -e '\033[32mOK\033[0m' || { echo -e '\033[31mFAIL\033[0m'; exit 1; }
```

Prevents a fourth AMOUNT_TO_PLAN regression at commit time.

### Bonus Step B (~5 min): Add note to CLAUDE.md

In `CLAUDE.md` §"Plan names + prices", after the current plan list, add one sentence:
> `AMOUNT_TO_PLAN` in `backend/routers/billing.py` must contain keys `{9900, 15000, 25000, 89900}` — these are the Stripe amount_total values (in cents) for current plan prices.

Prevents the disconnect that caused three failed fixes.

---

## What This Replaces

Runs 31 and 32 active directions (same GH #181 fix). Run 33 adds: CI-trap evidence (1553bf7 wired contradictory tests this morning), third missed commit confirmation (2174732), and run 32 question answers (dashboard/conversations coverage confirmed).

---

## Standing Sprint Direction (unchanged)

`/moratorium-sprint` remains the standing highest-leverage action:
- Items A (check_project_invariants pre-commit, ~5 min) + B (widget sync guard, ~15 min) + D (CI eval workflow, ~20 min)
- Pending 9→5→2 after sprint + governance audit → moratorium exits at ≤ 2
- moratorium-sprint SKILL.md ready (7985fbb)
- Run 33 does not supersede this direction — implement both in any interactive session

---

## Confidence

**HIGH** — Four independent evidence sources confirmed this run:
1. Direct AMOUNT_TO_PLAN inspection: 15000 and 25000 absent
2. GH #181 filed and open
3. Three commits (c72b535, 1eaaeec, 2174732) missed entries despite being titled as billing fixes
4. test_billing_amount_to_plan.py confirmed to have CI-blocking contradictory methods (lines 38, 42)

Debate: SURVIVES 3 rounds. All three challenges to Idea 1 overruled. /moratorium-sprint WEAKENED to standing action (9th consecutive rec, no new forcing evidence this run).
