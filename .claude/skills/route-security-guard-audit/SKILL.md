---
name: route-security-guard-audit
description: Audit FastAPI routers for missing block_demo_role and ai_usage_guard dependencies. Use when adding new routers, reviewing PRs with new endpoints, or after GH issues flag missing security guards.
version: 1.0.0
origin: subconscious-run-105
user-invocable: true
triggers:
- route-security-guard-audit
- security guard audit
- missing block_demo_role
- missing ai_usage_guard
effort: low
---

# Route Security Guard Audit

Checks `backend/routers/` for mutating endpoints missing `block_demo_role` or AI-invoking routes missing `ai_usage_guard`. Recurring pattern: GH #643 (appointment_briefs.py, 2026-08-11), GH #661 (scoring_config.py, 2026-08-16).

## Step 1 — Inventory existing guards

```bash
# Which routers already import block_demo_role?
grep -rl "block_demo_role" backend/routers/

# Which routers already import ai_usage_guard?
grep -rl "ai_usage_guard" backend/routers/

# Where is block_demo_role defined?
grep -rn "def block_demo_role" backend/
```

Note the baseline. Any router NOT in this list is a candidate for review.

## Step 2 — Find mutating routes missing block_demo_role

```bash
# All routers with POST/PUT/PATCH/DELETE that don't import block_demo_role
for f in backend/routers/*.py; do
  if grep -qE "@router\.(post|put|patch|delete)" "$f"; then
    if ! grep -q "block_demo_role" "$f"; then
      echo "MISSING block_demo_role: $f"
    fi
  fi
done
```

For each flagged file, check whether the routes are truly mutating (not just read endpoints declared under a non-GET method). Exclude routers that handle only internal/admin traffic not accessible to demo tenants.

## Step 3 — Find AI-invoking routes missing ai_usage_guard

```bash
# Routers that call Claude/AI but don't import ai_usage_guard
for f in backend/routers/*.py; do
  if grep -qE "claude|anthropic|llm|ai_service" "$f"; then
    if ! grep -q "ai_usage_guard" "$f"; then
      echo "MISSING ai_usage_guard: $f"
    fi
  fi
done
```

Cross-reference against `backend/services/ai_usage_guard.py` to confirm the guard is plan-gated for the relevant plan tiers.

## Step 4 — Assess business impact

For each flagged router:
- What data does it mutate? (leads, appointments, messages, configs)
- Which plan tiers can reach it?
- Is there a demo tenant in production that could reach this endpoint?
- What's the blast radius if a demo tenant writes here? (data leak, billing bypass, phantom leads)

Score: HIGH (demo tenant can mutate live data) / MEDIUM (limited scope) / LOW (internal only).

## Step 5 — Add block_demo_role dependency pattern

For HIGH/MEDIUM findings, add the guard as a FastAPI `Depends()`:

```python
from backend.dependencies.auth import block_demo_role

# Before (mutating route with no guard):
@router.post("/appointments")
async def create_appointment(
    data: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    ...

# After (with guard):
@router.post("/appointments")
async def create_appointment(
    data: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    _: None = Depends(block_demo_role),
):
    ...
```

The `_: None = Depends(block_demo_role)` pattern is the established convention (see `backend/routers/leads.py` for reference). The guard raises HTTP 403 for demo tenants before the route body executes.

## Step 6 — Add structural test

After adding guards, confirm coverage in `backend/tests/test_plan_gating_new_plans.py`:

```python
def test_demo_tenant_blocked_from_new_router():
    """Demo tenants must not be able to mutate data via newly added routes."""
    response = client.post(
        "/api/new-endpoint",
        json={"field": "value"},
        headers={"Authorization": f"Bearer {DEMO_TENANT_TOKEN}"},
    )
    assert response.status_code == 403
    assert "demo" in response.json()["detail"].lower()
```

Run the test suite to verify:
```bash
python -m pytest backend/tests/test_plan_gating_new_plans.py -x -q
```

## Output format

File GH issue if findings exist (severity HIGH or MEDIUM):

```
Title: security: [router name] missing block_demo_role on mutating endpoints
Body:
- Affected file: backend/routers/<name>.py
- Routes: POST /path1, PUT /path2 (list all)
- Risk: demo tenant can [specific action]
- Fix: add Depends(block_demo_role) per SKILL.md Step 5 pattern
- Test: add test_plan_gating_new_plans.py case per SKILL.md Step 6
Labels: security, backend
```

## Known open issues
- GH #643: appointment_briefs.py (draft PR #653)
- GH #661: scoring_config.py (no PR yet as of 2026-08-17)

## Cross-refs
- `backend/dependencies/auth.py` — block_demo_role definition
- `backend/services/ai_usage_guard.py` — ai_usage_guard definition
- `backend/tests/test_plan_gating_new_plans.py` — structural test home
- `.claude/rules/schema-discipline.md` — related security invariants
- `docs/dev-knowledge/bug-patterns.md` — for logging new findings
