# Winning Concept — 2026-05-25 (Run 33)

## Recommendation

Fix GH #181: add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py`, and replace the two contradictory test methods in `backend/tests/test_billing_amount_to_plan.py` that actively block CI from going green on a correct fix.

---

## Why This, Why Now

**Three consecutive subconscious runs (31, 32, 33) confirm the same gap.** AMOUNT_TO_PLAN in `billing.py` has `9900→growth` and `89900→enterprise` (correct current prices) but is missing `15000→autopilot` ($150/mo) and `25000→professional` ($250/mo). CLAUDE.md §"Plan names + prices" documents these as current plan prices. Tenants at these price points without `metadata.plan` in their Stripe webhook payload resolve to `None` in `_resolve_plan()` — silent plan misclassification at the billing layer.

**The CI trap makes this urgent today, not just important.** Commit 1553bf7 wired `test_billing_amount_to_plan.py` into CI on 2026-05-23. The file contains `test_no_wrong_15000_mapping` which asserts `15000 not in AMOUNT_TO_PLAN`. A developer working on auth.py (1590 lines, next refactor target), seeing CI red on their PR after adding the correct billing entries, will likely revert the fix — trusting the test over their instinct. The CI signal is actively inverted. Every day of inaction increases revert-risk as PR volume picks back up after the god-class refactor sprint.

**Zero implementation blockers.** S-effort (~15 min). No migration. No new dependencies. No architectural change. Two dict entries + four test method edits. Full implementation sketch exists in subconscious/runs/2026-05-23-pm/winning-concept.md. GH #181 body also documents the exact fix. Nightly review confirmed this cannot be auto-applied (MEDIUM billing risk, human approval required) — making human-initiated execution the only path.

**RUN 34 MANDATE:** If GH #181 remains unimplemented after run 33, run 34 MUST switch mechanism — authorize nightly review to apply the billing.py dict addition as LOW-risk additive change (per governance precedent: four consecutive same-winner runs → mechanism change). Test correction (removing contradictory assertions) would be bundled as LOW-risk test hygiene.

---

## Implementation Sketch

**Estimated time: ~15 min**

### Step 1: Add missing entries to billing.py

File: `backend/routers/billing.py` around line 263.

Current `# Monthly only (current pricing)` block:
```python
AMOUNT_TO_PLAN: dict[int, str] = {
    # Monthly only (current pricing)
    9900: "growth",
    89900: "enterprise",
```

Add the two missing entries:
```python
AMOUNT_TO_PLAN: dict[int, str] = {
    # Monthly only (current pricing)
    9900: "growth",
    15000: "autopilot",    # $150/mo current price (CLAUDE.md)
    25000: "professional", # $250/mo current price (CLAUDE.md)
    89900: "enterprise",
```

### Step 2: Fix contradictory tests in test_billing_amount_to_plan.py

**Remove** these two methods (lines ~38-44):
```python
def test_no_wrong_15000_mapping(self):
    """Issue #81 claimed 15000->professional was present; verify it is NOT."""
    assert 15000 not in AMOUNT_TO_PLAN, "15000 should not be in AMOUNT_TO_PLAN"

def test_no_wrong_25000_mapping(self):
    """Issue #81 claimed 25000->enterprise was present; verify it is NOT."""
    assert 25000 not in AMOUNT_TO_PLAN, "25000 should not be in AMOUNT_TO_PLAN"
```

**Add** positive correctness assertions in their place:
```python
def test_current_autopilot_price(self):
    """$150/mo autopilot — current price from CLAUDE.md."""
    assert AMOUNT_TO_PLAN[15000] == "autopilot"

def test_current_professional_price(self):
    """$250/mo professional — current price from CLAUDE.md."""
    assert AMOUNT_TO_PLAN[25000] == "professional"
```

### Step 3: Update test_all_four_current_tiers_present

The current assertion checks `{24900, 29900, 49900, 89900}` (legacy prices). Update to check current prices:
```python
def test_all_four_current_tiers_present(self):
    current_prices = {9900, 15000, 25000, 89900}  # growth, autopilot, professional, enterprise
    for amount in current_prices:
        assert amount in AMOUNT_TO_PLAN, f"{amount} missing from AMOUNT_TO_PLAN"
```

### Step 4: Update docstring

Replace the module docstring's "Current state inspection" paragraph to reflect the corrected state after fix is applied. Remove "Issue #81 can be closed" text — it's now contradicted by reality.

### Step 5: Close GH #181

After CI passes: close GH #181 with reference to the fixing commit.

---

## What This Replaces

Previous active directions: runs 31 and 32 had the same winner. Run 33 reissues with a new mandate trigger (run 34 mechanism change if unimplemented).

---

## Confidence: HIGH

Evidence sources: (1) direct grep of billing.py confirms 15000+25000 absent, (2) direct read of test_billing_amount_to_plan.py confirms contradictory assertions, (3) nightly review 2026-05-25 confirmed GH #181 still open with no fix, (4) two prior subconscious runs with same finding, (5) CLAUDE.md §"Plan names + prices" is the authoritative source. Debate: Idea 1 SURVIVES (3 rounds), Idea 2 WEAKENED (moratorium + M-effort), Idea 3 WEAKENED (commitment bottleneck confirmed).
