---
name: route-security-guard-audit
description: Audit FastAPI route security coverage for the centralized demo-role mutation middleware, route-local high-risk guards, and AI usage guards. Use when adding routers, reviewing endpoint changes, or triaging security-guard findings.
version: 1.1.0
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

Audit `backend/routers/` without assuming every mutating router must import `block_demo_role`.

The primary demo-role mutation control is `backend/middleware/demo_role_guard.py::DemoRoleBlockMiddleware`, registered in `backend/main.py`. It blocks verified `role=demo` JWTs from POST/PUT/PATCH/DELETE outside the explicit allowlist. Route-local `block_demo_role` remains belt-and-suspenders protection for money/destructive endpoints that live under an allowlisted prefix such as `/api/v1/auth`.

AI-invoking routes still require separate review for `ai_usage_guard`; the centralized demo middleware does not replace plan/token enforcement.

## Step 1 — Verify the centralized demo mutation guard first

Before flagging routers, verify all three invariants:

```bash
# Middleware implementation exists
grep -n "class DemoRoleBlockMiddleware" backend/middleware/demo_role_guard.py

# Middleware is registered by the app
grep -n "DemoRoleBlockMiddleware" backend/main.py

# Project invariant checker knows about the registration
grep -n "DemoRoleBlockMiddleware" scripts/check_project_invariants.py
```

Inspect `DEMO_MUTATION_ALLOWLIST_PREFIXES` in `backend/middleware/demo_role_guard.py`. If the middleware is absent, unregistered, or broadened unsafely, treat that as the primary finding instead of opening dozens of router-local issues.

## Step 2 — Review mutating routes by middleware coverage

For POST/PUT/PATCH/DELETE routes, ask:

1. Is the route outside `DEMO_MUTATION_ALLOWLIST_PREFIXES`? If yes, the centralized middleware is the primary demo-role control; **do not flag the router merely because it lacks `Depends(block_demo_role)`**.
2. Is the route under an allowlisted prefix? If yes, determine whether demo writes are intentionally permitted (public ingress/auth/widget/book flows) or whether the endpoint is money/destructive/account-sensitive and therefore needs a route-local `block_demo_role` dependency.
3. Does the route bypass the FastAPI app/middleware path entirely? If so, review that ingress separately.

Useful inventory:

```bash
grep -RnoE '@router\.(post|put|patch|delete)' backend/routers/
grep -Rno "block_demo_role" backend/routers/ backend/dependencies.py
```

A missing router-local import is not a finding by itself.

## Step 3 — Verify high-risk allowlisted-prefix routes retain local guards

The `/api/v1/auth` prefix is allowlisted for login/OAuth/password-reset flows, so money/destructive endpoints under that prefix must keep local protection.

For each such endpoint, inspect FastAPI dependencies and confirm `block_demo_role` is present where demo access would create financial, destructive, or account-level effects.

Established pattern:

```python
from backend.dependencies import block_demo_role

@router.post("/sensitive-action")
async def sensitive_action(
    ...,
    _: None = Depends(block_demo_role),
):
    ...
```

Do not duplicate this dependency across ordinary dashboard routers already covered by `DemoRoleBlockMiddleware` unless there is a specific defense-in-depth reason.

## Step 4 — Find AI-invoking routes missing ai_usage_guard

```bash
for f in backend/routers/*.py; do
  if grep -qiE 'claude|anthropic|llm|ai_service|model_client' "$f"; then
    if ! grep -q "ai_usage_guard" "$f"; then
      echo "REVIEW ai_usage_guard: $f"
    fi
  fi
done
```

This is a review candidate list, not an automatic violation list. Confirm the route actually initiates paid/plan-metered model work and whether enforcement occurs at the router, shared dependency, or called service before filing an issue.

## Step 5 — Assess business impact

For each real gap:
- Which request path and HTTP method are affected?
- Which control should apply: centralized demo middleware, route-local `block_demo_role`, `ai_usage_guard`, or another shared gate?
- Which tenant/plan can reach it?
- Is the path intentionally allowlisted/public?
- What is the concrete blast radius: financial action, destructive mutation, data integrity, or paid-model bypass?

Score HIGH / MEDIUM / LOW from reachable impact, not from a grep-only absence.

## Step 6 — Test the control at the correct layer

For centralized demo-role behavior, prefer tests around `DemoRoleBlockMiddleware` / app registration and representative blocked + allowlisted paths. For a high-risk allowlisted-prefix endpoint, assert the route-local dependency remains attached. For AI usage enforcement, test the actual metering/plan gate used by the route or service.

Relevant checks:

```bash
python -m pytest backend/tests/test_plan_gating_new_plans.py -x -q
python scripts/check_project_invariants.py
```

Add a focused regression test when the finding exposes behavior not already protected structurally.

## Output format

File an issue only for a verified control gap:

```text
Title: security: <specific control gap>
Body:
- Affected path/file: <path + source file>
- Method/control: <POST/PUT/PATCH/DELETE; middleware/local guard/AI guard>
- Reachability: <who can reach it and why existing shared controls do not apply>
- Risk: <specific effect>
- Fix: <smallest correct control-layer change>
- Test: <focused regression or invariant>
Labels: security, backend
```

Do not open one issue per router simply because `block_demo_role` is absent. Deduplicate against existing issues and account for centralized middleware before reporting.

## Historical note

GH #669 originally reported 95 routers missing route-local `Depends(block_demo_role)`. That detector assumption became stale after the repository adopted `DemoRoleBlockMiddleware` as the class-wide fix. Future audits must evaluate middleware coverage and its allowlist instead of recreating that false-positive pattern.

## Cross-refs
- `backend/middleware/demo_role_guard.py` — centralized demo mutation guard + allowlist
- `backend/main.py` — middleware registration
- `backend/dependencies.py` — route-local `block_demo_role`
- `backend/services/ai_usage_guard.py` — AI plan/token enforcement
- `backend/tests/test_plan_gating_new_plans.py` — plan/security structural tests
- `scripts/check_project_invariants.py` — app/security invariants
- `.claude/rules/schema-discipline.md` — related security invariants
- `docs/dev-knowledge/bug-patterns.md` — durable bug-pattern notes
