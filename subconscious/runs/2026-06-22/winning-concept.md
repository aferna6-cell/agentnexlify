# Winning Concept — 2026-06-22 (Run 65)

## Recommendation

Add plan-name guard Check 7 to `scripts/check_project_invariants.py` — verify `chatbot` and `agent_os` appear in the plan-gating constants that gate SMS, Zapier, and premium features.

## Why This, Why Now

The GH #292/#293 fix (`57f2bb4`, 2026-06-22) resolved a 6-day production regression where all new `agent_os` tenants ($99.99/mo) had NO premium features after the 2026-06-15 repricing. The test suite now locks the constants (test_plan_gating_new_plans.py, 90 tests), but tests run at PR time — not at every commit. check_project_invariants.py runs at pre-commit (Check 13, wired by `bc91e97`), catching violations before they even reach CI. This guard is the explicit Bonus B from run 64's winning-concept.md, with the pre-condition (GH #292/#293 implemented) now met. Future repricings, plan renames, or new plan introductions will silently break these gates again without a commit-time invariant. S-effort (~15 lines Python, ~30 min), AUTONOMOUS-EXECUTABLE via the same nightly review channel that implemented Check 13.

## Implementation Sketch

1. **Open `scripts/check_project_invariants.py`** and locate the end of the existing checks.

2. **Append Check 7 block** (~15 lines):

```python
# Check 7: New plan names appear in plan-gating constants
import importlib
import sys as _sys

def _check_plan_gating_constants():
    required_plans = {"chatbot", "agent_os"}
    errors = []
    # SMS rate limiter
    try:
        from backend.services.sms_rate_limiter import _UNLIMITED_PLANS
        missing = required_plans - _UNLIMITED_PLANS
        if missing:
            errors.append(f"sms_rate_limiter._UNLIMITED_PLANS missing: {missing}")
    except Exception as e:
        errors.append(f"Could not import sms_rate_limiter: {e}")
    # API key auth (Zapier gate)
    try:
        from backend.services.api_key_auth import _ALLOWED_PLANS
        missing = required_plans - _ALLOWED_PLANS
        if missing:
            errors.append(f"api_key_auth._ALLOWED_PLANS missing: {missing}")
    except Exception as e:
        errors.append(f"Could not import api_key_auth: {e}")
    return errors

_plan_errors = _check_plan_gating_constants()
if _plan_errors:
    print("FAIL plan-name guard: new plans missing from gating constants")
    for e in _plan_errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("PASS plan-name guard: chatbot + agent_os in all gating constants")
```

3. **Run locally** to confirm `PASS plan-name guard: chatbot + agent_os in all gating constants`.

4. **Commit** with message: `guard: Add plan-name Check 7 to check_project_invariants.py — gates chatbot+agent_os (post #292/#293)`

5. **Update governance.json** — mark this run's active_direction as AUTONOMOUS-EXECUTABLE; nightly review can apply if human doesn't.

## What This Replaces

Previous active directions: GH #292/#293 (IMPLEMENTED `57f2bb4`) and GH #308 (IMPLEMENTED `3a958e5`). This run is the first free-choice run since the 2026-06-15 repricing. No mandate fires. Winning concept is a direct consequence of what we just fixed — close the loop with a systemic guard.

## RUN 66 MANDATE

If Check 7 still unimplemented by run 66: winner stays Check 7 (no mandate switch — this is S-effort with no competing moratorium_override items). Nightly review authorized for AUTONOMOUS execution (same class as Check 13 by `bc91e97`).

## Confidence

HIGH — pre-condition confirmed by direct code verification (`57f2bb4` present in git log), autonomous execution channel confirmed active (Check 13 via nightly), implementation sketch is explicit and bounded.
