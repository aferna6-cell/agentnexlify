# Run 103 — Winning Concept (2026-08-13-pm)

## Fix `backend/routers/appointment_briefs.py` — Add `block_demo_role` + `ai_usage_guard` + Structural Test

**Category:** code_health
**Effort:** XS (~15 min to apply + test)
**Confidence:** HIGH
**Status:** AUTONOMOUS-EXECUTABLE — nightly can apply without human approval

---

## Problem

`appointment_briefs.py` generates AI-powered appointment briefs via Claude API. Demo tenants can call this endpoint today, consuming production AI quota at zero cost. The `block_demo_role` guard is absent. No `ai_usage_guard` call before the Claude API call. No structural test enforcing the guard.

**Confirmed evidence:**
- `backend/routers/appointment_briefs.py`: `Depends(_get_current_tenant)` only. `block_demo_role` absent. `ai_usage_guard` absent.
- GH #643 open 7 days: "MEDIUM: appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard" — labeled `ai-ready`, `security`, `medium-risk`, `nightly-review`. No linked PR.
- Autopilot stalled (#399 expired): normal fix queue offline.
- Pattern proven: c204af2 (2026-08-08) applied identical guard to billing_usage.py — same execution path.
- nightly-2026-08-13: Step 9D confirms #643 as top open blocker, autopilot 5/5 failures.
- route-security-guard-audit SKILL.md (proposed run 102, PR #653 open) documents exact steps.

**Cost of inaction:** every nightly run that fires will re-identify this gap. Each cycle is wasted discovery time + continued demo-tenant exploit window.

---

## Implementation Plan

### Step 1 — Add import (if missing)
In `backend/routers/appointment_briefs.py`, verify:
```python
from backend.dependencies import block_demo_role
```
Check `billing.py:33` for canonical import reference.

### Step 2 — Add guard to route decorator
For the primary endpoint (`@router.post("/{tenant_id}/{appointment_id}/brief")`):
```python
@router.post(
    "/{tenant_id}/{appointment_id}/brief",
    dependencies=[Depends(block_demo_role)]
)
```
Apply to ALL endpoints in the router that call Claude API or modify billing state.

### Step 3 — Add ai_usage_guard call
Inside the handler, before any `client.messages.create()` call:
```python
await ai_usage_guard(client_id=claims["client_id"], estimated_tokens=500)
```
Reference `billing_usage.py` for canonical placement pattern.

### Step 4 — Add structural test
In `backend/tests/test_plan_gating_new_plans.py`:
```python
def test_block_demo_role_guard_on_appointment_briefs():
    app_routes = {route.path: route for route in app.routes}
    route = app_routes.get("/api/v1/appointments/{tenant_id}/{appointment_id}/brief")
    assert route is not None, "Route not found"
    dep_funcs = [dep.dependency for dep in (route.dependencies or [])]
    assert block_demo_role in dep_funcs, (
        "block_demo_role guard missing from /api/v1/appointments brief endpoint"
    )
```

### Step 5 — Syntax verification
```bash
python -c "import ast; ast.parse(open('backend/routers/appointment_briefs.py').read())"
python -m pytest backend/tests/test_plan_gating_new_plans.py -k "test_block_demo_role_guard_on_appointment_briefs" -v
```
Both must pass clean.

### Step 6 — Commits
```
fix(security): add block_demo_role + ai_usage_guard to appointment_briefs.py
test: assert block_demo_role guard on appointment_briefs endpoints
```
Or combined: `fix(security): add block_demo_role + ai_usage_guard to appointment_briefs + structural test`

### Step 7 — Close GH #643
After merge, comment on #643: "Fixed in <commit>. block_demo_role + ai_usage_guard added to appointment_briefs.py. Structural test added to test_plan_gating_new_plans.py."

---

## Canonical References

- `backend/routers/billing.py:33` — block_demo_role import + usage pattern
- `backend/routers/billing_usage.py` — c204af2 identical guard application
- `backend/dependencies.py` — block_demo_role definition
- `backend/tests/test_plan_gating_new_plans.py` — structural test file
- GH #643 — issue to close after fix

---

## Why This Wins

1. **Confirmed gap**: grep proves absence. Not speculation.
2. **XS effort**: identical to c204af2 — known 15-min execution path.
3. **Autonomous execution**: AUTONOMOUS-EXECUTABLE label means nightly applies without waiting on #399 secret rotation.
4. **Closes open issue**: #643 has been open 7 days with no path to resolution. This is that path.
5. **No implementation risk**: adding a dependency guard + existing test pattern — no new logic, no schema changes.
6. **Route-security-guard-audit SKILL.md (PR #653) already documents exactly how**: zero re-discovery cost for nightly executor.

---

## Anti-Patterns to Avoid

- Never add guard after business logic executes — must be in `dependencies=[]`, not inside the handler
- Never mock `block_demo_role` in tests that are asserting its presence
- Never skip the structural test — it prevents the guard from being silently removed again

---

## Next Action

Nightly session applies this fix autonomously next cycle (AUTONOMOUS-EXECUTABLE). Human approval NOT required. Executor references:
- `backend/routers/billing.py:33` for canonical pattern
- `backend/routers/billing_usage.py` for c204af2 precedent
- `backend/tests/test_plan_gating_new_plans.py` for test placement
