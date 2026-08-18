# Run 103 — Winning Concept (2026-08-12)

## Create `.claude/skills/route-security-guard-audit/SKILL.md`

**Category:** code_health
**Effort:** S (~30 min to write well)
**Confidence:** HIGH
**Status:** RECOMMENDED — awaiting human approval before execution

---

## Problem

The `block_demo_role` FastAPI dependency guard prevents demo tenants from executing billing and payment operations. It must be present on every endpoint that mutates billing state, account subscriptions, or AI usage quotas.

Evidence of recurrence:
- `cbbaae5` (2026-08-07): nightly session added guard to `billing_usage.py` on detached HEAD — commits orphaned, fix never merged
- `c204af2` (2026-08-08): same fix re-applied correctly after orphaned commit discovery
- `228203d` (2026-08-08): structural test added to prevent silent regression — same day
- GH #643 (open 2026-08-07, 5 days as of 2026-08-12): `appointment_briefs.py` missing `block_demo_role` + plan gate + `ai_usage_guard` — security+ai-ready labeled, autopilot loop stalled (AUTOPILOT_GH_TOKEN expired, GH #399)

Same 15-min re-discovery cost (billing.py:33 reference, test introspection pattern) paid twice in 48h. Without a skill, every new payment router will repeat this.

---

## Proposed SKILL.md Content

```markdown
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
```

---

## Why This Wins

1. **Evidence density:** 3 commits + 1 open GH issue + skill-discovery explicit proposal + 1 prior run pending approval = strongest evidence pattern in the run window.
2. **No existing coverage:** No SKILL.md covers this pattern. skill-discovery confirmed this before proposing.
3. **Prevents recurrence, not just fixes:** A SKILL.md file makes the pattern retrievable in 30 seconds instead of 15 minutes of re-discovery.
4. **Atomic:** One new file, no existing code touched, no implementation risk, human must approve before anything runs.
5. **GH #643 unblocked path:** Once AUTOPILOT_GH_TOKEN is rotated, issue-to-pr-loop can reference this skill in its implementation. Even before that, a human can invoke it manually.
6. **1-run carry-forward (not a loop):** Run 102 was the first recommendation; this is first carry-forward. Governance moratorium fires at 3+ consecutive same-winner runs, not 2.

---

## Governance Corrections This Run

| Item | Previous State | Corrected State |
|------|---------------|-----------------|
| KB freshness | FAIL (19d stale) | RESOLVED — Step 9G triggered compile, 114→124 articles 2026-08-12 |
| Detached HEAD guard | Proposed | CONFIRMED IMPLEMENTED — nightly SKILL.md lines 116+190 |
| response_score.py (mandate item 1) | Unverified | N/A — file does not exist; mandate item closed |
| PR pile-up | 5 drafts | UNCHANGED — 5 drafts (#575/#606/#611/#613/#626) |
| GH #643 | Open 4d (run 102) | Open 5d — STALLED, AUTOPILOT_GH_TOKEN expired |

---

## Next Action (for human approval)

Write `.claude/skills/route-security-guard-audit/SKILL.md` with the content above.

This is a documentation-only change. Does not modify any backend code. Does not touch billing, auth, or payments. Creates one new skill file.

Estimated effort: 30 minutes including validation pass.
