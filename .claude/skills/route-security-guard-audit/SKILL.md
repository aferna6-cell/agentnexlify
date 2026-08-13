# Route Security Guard Audit

## Trigger
- New FastAPI billing/payment/account-mutation endpoint added or modified
- Nightly review flags missing security dependency on payment route
- GH issue labeled `security` + `ai-ready` references `block_demo_role`
- Any router file in `backend/routers/` touched in a PR that adds AI usage

## What this skill does
Audits payment-adjacent routers for mandatory security guards, adds missing guards,
adds structural assertions to the test suite to prevent silent regression.

## Step 1 — Build guard inventory
```bash
grep -rn "block_demo_role" backend/routers/
```
Compare output against billing.py:33 (canonical reference pattern):
```python
@router.post("/endpoint", dependencies=[Depends(block_demo_role)])
```

## Step 2 — Identify missing guards
For each billing/payment/account endpoint (typically in: billing.py, billing_usage.py,
appointment_briefs.py, any router that calls stripe_service, ai_usage_guard, or
modifies subscriptions): verify `block_demo_role` is in the route's `dependencies`.

If missing: proceed to Step 3.

## Step 3 — Add guard
In the router file:
1. Add import if missing:
   ```python
   from backend.dependencies import block_demo_role
   ```
2. Add to route decorator:
   ```python
   @router.post("/endpoint", dependencies=[Depends(block_demo_role)])
   ```
3. For routes that also handle AI token usage, add `ai_usage_guard` call inside the handler before any Claude API call:
   ```python
   await ai_usage_guard(client_id=client_id, estimated_tokens=500)
   ```

## Step 4 — Add structural test assertion
In `backend/tests/test_plan_gating_new_plans.py`, add an assertion that introspects
the route's `dependencies` list:
```python
def test_block_demo_role_guard_on_<endpoint>():
    app_routes = {route.path: route for route in app.routes}
    route = app_routes.get("/api/<endpoint-path>")
    assert route is not None, "Route not found"
    dep_funcs = [dep.dependency for dep in (route.dependencies or [])]
    assert block_demo_role in dep_funcs, (
        "block_demo_role guard missing from /api/<endpoint-path>"
    )
```

## Step 5 — Syntax verification
```bash
python -c "import ast; ast.parse(open('backend/routers/<file>.py').read())"
```
Must succeed with no output (clean parse).

## Step 6 — Commit
Two commits:
1. `fix: add block_demo_role guard to <endpoint>`
2. `test: assert block_demo_role guard on <endpoint>`

Or one combined: `fix(security): add block_demo_role + ai_usage_guard to <endpoint> + structural test`

## Canonical reference
`backend/routers/billing.py:33` — the original correct pattern. When in doubt, match exactly.

## Anti-patterns
- Never add guard after business logic executes — must be in `dependencies=[]`, not inside the handler
- Never mock `block_demo_role` in tests that are asserting its presence
- Never skip the structural test — it prevents the guard from being silently removed

## Cross-refs
- `backend/dependencies.py` — `block_demo_role` definition
- `backend/tests/test_plan_gating_new_plans.py` — canonical test file
- GH #643 — first incident that motivated this skill
- `.claude/rules/schema-discipline.md` — invariants context
