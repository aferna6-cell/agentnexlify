# Winning Concept — 2026-05-23-pm (Run 32)

## Recommendation

Fix GH #181: add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py`, and replace the two contradictory test methods in `backend/tests/test_billing_amount_to_plan.py` that now actively block CI from going green after a correct fix.

---

## Why This, Why Now

**The billing fix is still incomplete.** AMOUNT_TO_PLAN has `9900: "growth"` and `89900: "enterprise"` (current prices, correct) but is missing `15000: "autopilot"` ($150/mo) and `25000: "professional"` ($250/mo). CLAUDE.md documents these as the current plan prices. Tenants at these price points without `metadata.plan` in their Stripe webhook resolve to `None` in `_resolve_plan()`.

**1eaaeec made it worse.** Commit 1eaaeec (this morning) was titled "Fix billing AMOUNT_TO_PLAN" and removed the wrong legacy mappings (correct) but still did not add 15000 and 25000. This is now two consecutive billing commits that miss the same entries — confirming the fix is non-obvious without explicit guidance pointing to CLAUDE.md plan prices.

**CI is now a booby trap.** Commit 1553bf7 (nightly review 2026-05-23) wired test_billing_amount_to_plan.py into CI. The file contains `test_no_wrong_15000_mapping` which asserts `15000 not in AMOUNT_TO_PLAN`. Any developer who adds the correct entry tomorrow will see CI go red on that test and may revert the fix — believing the test is correct and their change is wrong. The test's docstring compounds this by calling the legacy 24900/29900/49900 prices "current pricing."

**S-effort, moratorium-safe, isolated.** No migration, no new dependencies, no architectural change. Two dict entries and four test method edits. Closes GH #181.

---

## Implementation Sketch

**Total estimated time: ~15 min**

### Step 1: Add missing entries to billing.py

In `backend/routers/billing.py`, locate `AMOUNT_TO_PLAN` (line ~263). The `# Monthly only (current pricing)` block currently has only `9900` and `89900`. Add the two missing entries:

```python
AMOUNT_TO_PLAN: dict[int, str] = {
    # Monthly only (current pricing)
    9900: "growth",
    15000: "autopilot",    # ADD: $150/mo current price (CLAUDE.md)
    25000: "professional", # ADD: $250/mo current price (CLAUDE.md)
    89900: "enterprise",
    # Legacy monthly pricing (keep for existing subscribers)
    24900: "growth",
    29900: "autopilot",
    49900: "professional",
    19900: "growth",
    39900: "professional",
    79900: "enterprise",
    # Monthly + setup fee (legacy, setup now waived)
    ...
}
```

### Step 2: Fix the contradictory tests in test_billing_amount_to_plan.py

**Remove** these two methods (lines ~38-44, issue #81-era assertions that are now backwards):
- `test_no_wrong_15000_mapping` — asserts `15000 not in AMOUNT_TO_PLAN` (wrong)
- `test_no_wrong_25000_mapping` — asserts `25000 not in AMOUNT_TO_PLAN` (wrong)

**Add** two new methods:
```python
def test_current_autopilot_pricing_150(self):
    """$150/mo autopilot maps correctly (current price — CLAUDE.md, GH #181)."""
    assert AMOUNT_TO_PLAN[15000] == "autopilot"

def test_current_professional_pricing_250(self):
    """$250/mo professional maps correctly (current price — CLAUDE.md, GH #181)."""
    assert AMOUNT_TO_PLAN[25000] == "professional"
```

**Update** `test_all_four_current_tiers_present` to use actual current prices:
```python
def test_all_four_current_tiers_present(self):
    """All four current-price tiers must be present (CLAUDE.md plan prices)."""
    current_prices = {9900, 15000, 25000, 89900}  # $99, $150, $250, $899
    for amount in current_prices:
        assert amount in AMOUNT_TO_PLAN, f"${amount/100:.0f}/mo entry missing from AMOUNT_TO_PLAN"
```

**Update docstring** at top of file to clarify current vs legacy prices and reference GH #181.

### Step 3: Verify

```bash
python -m pytest backend/tests/test_billing_amount_to_plan.py -v
```

Expected: all tests pass, including the two new current-price assertions. No test should assert that 15000 or 25000 are absent.

### Step 4: Commit

```
fix(billing): add current-price entries to AMOUNT_TO_PLAN, fix contradictory tests (GH #181)

15000 (autopilot, $150/mo) and 25000 (professional, $250/mo) were absent from
AMOUNT_TO_PLAN. Two previous commits (c72b535, 1eaaeec) touched this dict but
missed these entries. Tenants at current prices without metadata.plan resolved
to None in _resolve_plan().

Also removes test_no_wrong_15000_mapping + test_no_wrong_25000_mapping — these
were correct for issue #81 (removing wrong legacy mappings) but are now backwards:
they would cause CI to fail if a developer adds the correct entries.

Closes GH #181.
```

### Bonus Step (alongside, ~10 min): Add pre-commit billing sentinel

After the fix lands, add Check 11 to `scripts/hooks/pre-commit`:

```bash
# Check 11: Billing AMOUNT_TO_PLAN current-price sentinel
echo -n "Check 11: billing current-price entries present... "
python3 -c "
from backend.routers.billing import AMOUNT_TO_PLAN
required = {9900, 15000, 25000, 89900}
missing = required - set(AMOUNT_TO_PLAN.keys())
if missing:
    print('FAIL — missing entries:', missing)
    exit(1)
" 2>/dev/null || { echo -e "${RED}FAIL${NC}"; exit 1; }
echo -e "${GREEN}OK${NC}"
```

Prevents a third AMOUNT_TO_PLAN regression at commit time rather than CI time.

---

## What This Replaces

Run 31's active direction (same GH #181 fix). Run 32 adds the critical context of WHY two billing commits missed the entries (test docstring says legacy prices are "current") and WHY the CI is now a booby trap (1553bf7 wired contradictory tests into CI this morning).

---

## Standing Sprint Direction (unchanged from runs 28–31)

`/moratorium-sprint` remains the standing highest-leverage action:
- Items A (check_project_invariants pre-commit, ~5 min) + B (widget sync guard, ~15 min) + D (CI eval workflow, ~20 min)
- Pending 8→4 after sprint + governance audit → moratorium exits at ≤2
- moratorium-sprint SKILL.md ready (7985fbb)

---

## Confidence

**HIGH** — Four independent evidence sources: (1) direct AMOUNT_TO_PLAN inspection confirms missing entries; (2) GH #181 filed by nightly review; (3) 1eaaeec failed the fix on the same day, confirming non-obviousness; (4) 1553bf7 wired contradictory CI tests same morning. Fix is surgical, 15 min, reversible, moratorium-safe.
