# Winning Concept — 2026-05-23 (Run 31)

## Recommendation

Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `billing.py:281`,
and update `test_billing_amount_to_plan.py` to assert these mappings are correct — replacing
the contradictory assertions that actively certify the gap as intended behavior.

---

## Why This, Why Now

**The billing fix is incomplete.** c72b535 (run 30's trigger event) correctly removed the
wrong legacy entries but never added the current-price entries: `15000→autopilot` ($150/mo)
and `25000→professional` ($250/mo). GH #181 filed this morning by the nightly review confirms
the absence by direct code inspection.

**CI is certifying the broken state.** `test_billing_amount_to_plan.py` was written for
issue #81, which was about removing wrong entries (old $15k→professional mapping). Lines 38-44
explicitly assert `15000 NOT in AMOUNT_TO_PLAN` and `25000 NOT in AMOUNT_TO_PLAN`. Nightly
review (1553bf7) wired this file into CI — so CI now runs tests that actively verify the bug
is present. Any future fix that adds 15000 and 25000 would cause CI to fail until the test is
also updated.

**Live tenant impact.** `_resolve_plan()` falls through to amount-based lookup when
`metadata.plan` is absent. Tenants who subscribed before `metadata.plan` was introduced — or
whose webhooks lack the field — will return `None` on a `$150` or `$250` charge, causing silent
plan misidentification downstream. CLAUDE.md documents these as current plan prices.

**Moratorium-safe, S-effort.** Two dict entries and four test method updates. No architectural
change, no migration required, no dependency on sprint items.

---

## Implementation Sketch

**Total estimated time: ~15 min**

### Step 1: Inspect current state (already done — billing.py:263-281)

AMOUNT_TO_PLAN currently has: 9900 growth, 89900 enterprise, plus legacy entries.
Missing: 15000 autopilot, 25000 professional.

### Step 2: Add current-price entries to billing.py

In `backend/routers/billing.py` at line 265-266 (after `# Monthly only (current pricing)`):

```python
AMOUNT_TO_PLAN: dict[int, str] = {
    # Monthly only (current pricing)
    9900: "growth",
    15000: "autopilot",   # ADD: $150/mo current price
    25000: "professional", # ADD: $250/mo current price
    89900: "enterprise",
    # Legacy monthly pricing (keep for existing subscribers)
    ...
}
```

### Step 3: Update test_billing_amount_to_plan.py

**Remove** `test_no_wrong_15000_mapping` and `test_no_wrong_25000_mapping` (lines 38-44).
These were valid for issue #81 but are now backwards.

**Add** two new test methods:

```python
def test_current_autopilot_pricing_150(self):
    """$150/mo autopilot maps correctly (current price, added GH #181 fix)."""
    assert AMOUNT_TO_PLAN[15000] == "autopilot"

def test_current_professional_pricing_250(self):
    """$250/mo professional maps correctly (current price, added GH #181 fix)."""
    assert AMOUNT_TO_PLAN[25000] == "professional"
```

**Update** `test_all_four_current_tiers_present` to use current prices:

```python
def test_all_four_current_tiers_present(self):
    current_prices = {9900, 15000, 25000, 89900}  # $99, $150, $250, $899
    for amount in current_prices:
        assert amount in AMOUNT_TO_PLAN, f"{amount} missing from AMOUNT_TO_PLAN"
```

**Update** docstring at top of file to reference GH #181 and document current vs legacy prices.

### Step 4: Verify

```bash
python -m pytest backend/tests/test_billing_amount_to_plan.py -v
```

Expected: all tests pass including the two new current-price assertions.

### Step 5: Commit

```
fix(billing): add current-price entries to AMOUNT_TO_PLAN (GH #181)

Closes GH #181: c72b535 removed wrong legacy mappings but omitted the
current-price entries. Tenants at $150 (autopilot) and $250 (professional)
without metadata.plan were resolving to None in _resolve_plan().

Also updates test to assert these mappings are present (replaces
issue #81-era assertions that they should NOT be present).
```

---

## What This Replaces

Run 30's winning concept (billing constants contract tests) was partially addressed by the
nightly review wiring `test_billing_amount_to_plan.py` into CI. Run 31 completes the fix:

- Run 30: "add a test to guard AMOUNT_TO_PLAN" → nightly review wired existing test to CI ✓
- Run 31: "the existing test is guarding the wrong state — fix both the dict and the test" → this

After this fix:
- AMOUNT_TO_PLAN has all 4 current plan prices (9900, 15000, 25000, 89900)
- CI will catch any future drift on these values
- GH #181 can be closed

---

## Standing Sprint Direction (unchanged from runs 28–30)

`/moratorium-sprint` remains the standing highest-leverage action:
- Items A+B+D, ~40 min
- Pending 6→2 = moratorium exits after sprint
- moratorium-sprint SKILL.md ready (7985fbb)
- Invoke /moratorium-sprint in any interactive session

---

## Confidence

**HIGH** — Three independent evidence sources (nightly review GH #181, direct AMOUNT_TO_PLAN
inspection, test file lines 38-44 contradicting correct state). Fix is surgical, reversible,
tested. S-effort. Moratorium-safe. Extends the billing fix work already approved in c72b535.
