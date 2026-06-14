# Winning Concept — 2026-05-22-pm (Run 30)

## Recommendation

Add `backend/tests/test_billing_constants.py` — parametric contract tests for
AMOUNT_TO_PLAN and PLAN_TO_STRIPE_PRICE — and wire them into `pr-check.yml`.

---

## Why This, Why Now

**A live production billing bug was just fixed.** c72b535 (2026-05-22) corrected wrong
$150/$250 plan mappings and added the missing enterprise entry to AMOUNT_TO_PLAN. These
constants are the lookup table that identifies a tenant's plan from a Stripe amount — every
billing webhook, subscription event, and plan-gated feature depends on their accuracy. There
were no tests guarding them. The bug was found by a human reading the code, not by CI.

**The fix creates a contract worth encoding.** Now that the correct values are known and
committed (growth=$99, autopilot=$150, professional=$250, enterprise=$899), a test file that
asserts those values catches any future drift — price change, typo, copy-paste — before it
reaches production. The test is self-documenting: it tells the next engineer exactly what
AMOUNT_TO_PLAN is supposed to contain.

**The CI hook is primed.** 1eaaeec just added `backend/tests/test_local_seo_handlers.py`
to `pr-check.yml`. The pattern is live. Adding one more test target to the same workflow
is a 2-line change.

**Moratorium-safe.** This recommendation is S-effort (~20 min), code-only, no human
planning required, and doesn't depend on any moratorium sprint items. It advances the
codebase regardless of when the sprint runs.

---

## Implementation Sketch

**Total estimated time: ~20 min**

### Step 1: Read current billing constants
```bash
grep -n "AMOUNT_TO_PLAN\|PLAN_TO_STRIPE_PRICE\|growth\|autopilot\|professional\|enterprise" \
  backend/routers/billing.py | head -40
```

### Step 2: Create test file
File: `backend/tests/test_billing_constants.py`

```python
"""Contract tests for billing plan constants.

Guards AMOUNT_TO_PLAN and PLAN_TO_STRIPE_PRICE against silent drift.
When prices change, update the constants AND this test together.
"""
import pytest
from backend.routers.billing import AMOUNT_TO_PLAN, PLAN_TO_STRIPE_PRICE


# Documented plan prices — update here when pricing changes
EXPECTED_PLANS = {
    "growth": 99,
    "autopilot": 150,
    "professional": 250,
    "enterprise": 899,
}

PLAN_NAMES = set(EXPECTED_PLANS.keys()) | {"free"}


@pytest.mark.parametrize("plan_name,expected_amount", EXPECTED_PLANS.items())
def test_amount_to_plan_round_trips(plan_name, expected_amount):
    """Each documented plan amount maps back to the correct plan name."""
    assert AMOUNT_TO_PLAN.get(expected_amount) == plan_name, (
        f"AMOUNT_TO_PLAN[{expected_amount}] should be '{plan_name}', "
        f"got '{AMOUNT_TO_PLAN.get(expected_amount)}'"
    )


def test_amount_to_plan_contains_all_paid_plans():
    """All paid plans have an entry in AMOUNT_TO_PLAN."""
    mapped_plans = set(AMOUNT_TO_PLAN.values())
    for plan in EXPECTED_PLANS:
        assert plan in mapped_plans, f"'{plan}' missing from AMOUNT_TO_PLAN values"


def test_plan_to_stripe_price_contains_all_plans():
    """Every plan name in PLAN_NAMES has a Stripe price ID."""
    for plan in PLAN_NAMES:
        assert plan in PLAN_TO_STRIPE_PRICE, (
            f"'{plan}' missing from PLAN_TO_STRIPE_PRICE"
        )


def test_no_duplicate_amounts():
    """Each dollar amount maps to exactly one plan (no amount collision)."""
    amounts = list(AMOUNT_TO_PLAN.keys())
    assert len(amounts) == len(set(amounts)), "Duplicate amounts in AMOUNT_TO_PLAN"
```

### Step 3: Wire into CI
In `.github/workflows/pr-check.yml`, add to the pytest invocation:
```yaml
- name: Run billing constants tests
  run: python -m pytest backend/tests/test_billing_constants.py -v
```

Or if there's an existing `pytest backend/tests/` invocation, confirm it picks up the new file automatically (it will if the runner uses `pytest backend/tests/`).

### Step 4: Verify locally
```bash
python -m pytest backend/tests/test_billing_constants.py -v
```
Expected: all tests pass against the just-fixed constants.

### Step 5: Commit
```
chore(tests): add billing constants contract tests — guard AMOUNT_TO_PLAN against silent drift
```

---

## What This Replaces

No previous active direction is replaced. Run 29's standing sprint direction
(/moratorium-sprint, Items A+B+D) remains the highest-leverage action. Run 30 adds a
parallel fix that can proceed independently of the sprint.

This recommendation is the first evidence-backed, code-only win available since production
commits resumed (2026-05-22 after 17-day silence). It capitalizes on the billing fix's
timing — the correct values are now in code, making the test trivially writable.

---

## Standing Sprint Direction (unchanged from runs 28–29)

`/moratorium-sprint` remains the fastest path to moratorium exit:
- Items A+B+D, ~40 min
- Sprint reduces pending to 2 = exit condition met (≤ 2)
- moratorium-sprint SKILL.md ready (7985fbb)

---

## GH Issue Mechanism Evaluation (per run 29 Q1)

Run 29 asked: "If GH issue not created, consider freezing the write GH issue mechanism."
The issue was NOT created. Mechanism has been recommended as winner 3 times (runs 21, 29,
and now evaluated-but-not-chosen for run 30).

**Decision:** Do not formally freeze. The freeze_threshold applies to ideas killed in debate,
not to pending implementations. The issue spec is fully written. The mechanism is valid.

**But:** Do not propose as winner again until moratorium exits. The information is present.
The bottleneck is not another recommendation. Demoted to parking lot.

After moratorium exits (sprint invoked): the AI-to-Human Handoff GH issue should be the
first customer-value winner, given 36+ days stale + Critical gap all 7 verticals.

---

## Confidence

**HIGH** — Evidence is direct and fresh (c72b535 fixed a live billing bug today). Action is
specific (one test file, one CI entry). Scope is narrow (constants only, no billing logic).
Execution does not depend on moratorium resolution. S-effort. Highest-confidence winner since
run 14 (post-moratorium first pass).
