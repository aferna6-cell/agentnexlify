---
name: route-security-guard-audit
description: Audit FastAPI routers for missing block_demo_role and ai_usage_guard dependencies. 6-step checklist: grep inventory, identify gaps, add guard, add structural test, verify syntax, commit.
version: 1.0.0
origin: agentnexlify
user-invocable: true
triggers:
  - route security audit
  - block_demo_role audit
  - demo guard audit
  - security guard audit
  - audit routers
paths:
  - "backend/routers/**/*.py"
---

# Route Security Guard Audit

Systematic audit of FastAPI routers for missing `block_demo_role` and `ai_usage_guard` guards. Prevents demo tenants from mutating billing, payment, subscription, scoring, and AI-usage-critical endpoints.

## When to Use

- New FastAPI billing/payment/account-mutation endpoint added or modified
- Nightly review flags missing security dependency on a payment/scoring/AI route
- GH issue labeled `security` + `ai-ready` references `block_demo_role`
- Any router file in `backend/routers/` touched in a PR that adds AI usage or mutating endpoints
- Manual audit: user says "audit security guards", "check block_demo_role coverage"

## Background

`block_demo_role` prevents demo tenants from calling mutating endpoints. Without it, demo accounts can:
- Create/modify scoring factors (scoring_config.py — GH #661)
- Create/delete appointment briefs (appointment_briefs.py — GH #643)
- Modify any payment-adjacent resource

Canonical reference: `backend/routers/billing.py:33`

```python
from backend.dependencies import _get_current_tenant, require_role, block_demo_role
```

Confirmed-guarded routers: `billing.py`, `billing_usage.py`, `account_deletion.py`, `auth_billing.py`, `phone.py`

Known-unguarded (as of 2026-08-16): `appointment_briefs.py` (GH #643), `scoring_config.py` (GH #661)

---

## Step 1 — Build Guard Inventory

```bash
grep -rn "block_demo_role" backend/routers/
```

Record which files import and use `block_demo_role`. These are GUARDED.

```bash
grep -rn "ai_usage_guard" backend/routers/
```

Record which files call `ai_usage_guard`. These have AI usage protection.

---

## Step 2 — Identify Missing Guards

For each file in `backend/routers/` that:
- Has mutating endpoints (POST, PUT, DELETE, PATCH)
- Calls `stripe_service`, modifies subscriptions, creates/updates/deletes records, or calls the Claude API

Check whether `block_demo_role` is in the route dependencies. If not: FLAG.

Priority target list:
- `appointment_briefs.py` (GH #643 — known gap)
- `scoring_config.py` (GH #661 — known gap)
- Any router added after 2026-08-06 (Nexlify Score sprint)
- Any router with `ai_usage_guard` calls but no `block_demo_role`

---

## Step 3 — Add Guard

For each flagged endpoint:

```python
from backend.dependencies import _get_current_tenant, require_role, block_demo_role

@router.post("/endpoint", dependencies=[Depends(block_demo_role)])
async def create_thing(
    payload: ThingCreate,
    tenant: dict = Depends(_get_current_tenant),
):
    ...
```

For AI-usage-critical routes, also add `ai_usage_guard` call before Claude API invocation:

```python
from backend.dependencies import ai_usage_guard

# Before calling Claude:
await ai_usage_guard(tenant_id=tenant["client_id"], operation="thing_create")
```

---

## Step 4 — Add Structural Test

Add assertion in `backend/tests/test_plan_gating_new_plans.py`:

```python
def test_block_demo_role_guard_on_<endpoint_name>():
    """Demo tenants must not reach mutating endpoints on <router>."""
    app_routes = {route.path: route for route in app.routes}
    route = app_routes.get("/api/v1/<path>")
    assert route is not None, "Route /api/v1/<path> not found — was it removed?"
    dep_funcs = [dep.dependency for dep in (route.dependencies or [])]
    assert block_demo_role in dep_funcs, (
        "block_demo_role missing from /api/v1/<path> — demo tenants can mutate this endpoint"
    )
```

---

## Step 5 — Syntax Verification

```bash
python -c "import ast; ast.parse(open('backend/routers/<file>.py').read()); print('PASS')"
```

Also verify no `from __future__ import annotations` introduced (forbidden in FastAPI files — causes Pydantic 422 errors on all requests).

---

## Step 6 — Commit

```
fix(security): add block_demo_role to <router> endpoints
```

Include in commit body: GH issue reference if one exists, list of endpoints now guarded.

---

## Guardrails

- Never add `block_demo_role` to GET/read-only endpoints — read access for demo tenants is acceptable
- Never import `from __future__ import annotations` in FastAPI router files
- Never modify test to make it pass — if test fails, the code is wrong
- Check `client_id` not `tenant_id` in any new query (schema discipline rule)

## Cross-refs

- `backend/routers/billing.py:33` — canonical guard pattern
- `backend/dependencies.py` — block_demo_role, ai_usage_guard definitions
- `backend/tests/test_plan_gating_new_plans.py` — structural test file
- `.claude/rules/security-rules.md`
- GH #643 (appointment_briefs.py), GH #661 (scoring_config.py)
