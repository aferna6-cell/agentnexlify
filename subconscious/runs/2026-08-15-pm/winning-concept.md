# Run 105 — Winning Concept (2026-08-15-pm)

## Write `.claude/skills/route-security-guard-audit/SKILL.md` (Direct Escalation)

**Category:** code_health
**Effort:** XS (content ready in run 102 winning-concept.md — write one file, ~5 min)
**Confidence:** HIGH
**Status:** AUTONOMOUS-EXECUTABLE — 3rd carry-forward escalation (per runs 99/101 precedents)

---

## Problem

The `block_demo_role` FastAPI dependency guard prevents demo tenants from executing billing, payment,
and AI usage operations. Two confirmed routers are missing this guard:

1. `backend/routers/appointment_briefs.py` — GH #643 (open 8 days), draft PR #653 not merged
2. `backend/routers/scoring_config.py` — confirmed by grep (run 104 debate finding, no GH issue yet)

`scoring_config.py` has 4 mutating routes (`POST /api/v1/scoring`, `PUT /api/v1/scoring/{id}`,
`DELETE /api/v1/scoring/{id}`, `DELETE /api/v1/scoring`) with only `require_role("owner", "admin")`.
No `block_demo_role`, no `ai_usage_guard`. Demo tenants can manipulate scoring factors freely.

Without a skill encoding this pattern, every new router added to the codebase risks repeating
the same discovery cost: `billing.py:33` reference lookup → grep pattern → add guard → add structural
test → commit. Paid twice in 48h (runs 102-104 window). A SKILL.md makes this pattern retrievable
in 30 seconds instead of 15 minutes.

---

## Why This Run, Why This Winner

1. **3rd carry-forward = governance-mandated escalation.** `run_105_mandate` item 2: "3rd carry-forward —
   ESCALATE to AUTONOMOUS-EXECUTABLE per subconscious precedent (same path as Steps 9F → direct impl at
   run 99)." The threshold is met; escalation is not discretionary.

2. **Content already final.** `subconscious/runs/2026-08-11-pm/winning-concept.md` lines 28-112 contain
   the complete SKILL.md body. No drafting required — copy and write to file.

3. **Two live instances confirm the pattern.** `appointment_briefs.py` (GH #643) + `scoring_config.py`
   (grep-confirmed, run 104 finding) = recurring pattern, not isolated bug. Pattern = skill-worthy.

4. **Zero blast radius.** One new file in `.claude/skills/`. No existing code modified. No migrations.
   No test changes. No model calls. Fully reversible by deleting the file.

5. **Compounds immediately.** Once the SKILL.md exists, nightly-commit-review Step 5 can reference it,
   humans can invoke it directly, and issue-to-pr-loop can cite it in implementation sketches for GH #643.

---

## Implementation

Write the following to `.claude/skills/route-security-guard-audit/SKILL.md`:

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
appointment_briefs.py, scoring_config.py, any router that calls stripe_service, ai_usage_guard,
or modifies subscriptions): verify `block_demo_role` is in the route's `dependencies`.

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
3. For routes that also handle AI token usage, add `ai_usage_guard` call inside the handler
   before any Claude API call:
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

Or combined: `fix(security): add block_demo_role + ai_usage_guard to <endpoint> + structural test`

## Canonical reference
`backend/routers/billing.py:33` — the original correct pattern. Match exactly.

## Known gaps (as of 2026-08-15)
- `scoring_config.py` — /api/v1/scoring (4 mutating routes): no block_demo_role, no ai_usage_guard
- `appointment_briefs.py` — GH #643, draft PR #653 pending merge

## Anti-patterns
- Never add guard after business logic executes — must be in `dependencies=[]`, not inside handler
- Never mock `block_demo_role` in tests asserting its presence
- Never skip the structural test — prevents guard from being silently removed

## Cross-refs
- `backend/dependencies.py` — `block_demo_role` definition
- `backend/tests/test_plan_gating_new_plans.py` — canonical test file
- GH #643 — first incident that motivated this skill
- `.claude/rules/schema-discipline.md` — invariants context
```

---

## Bonus Actions (alongside winner commit)

1. **Open GH issue for scoring_config.py block_demo_role** — title: "fix(security): scoring_config.py
   missing block_demo_role on 4 mutating routes (/api/v1/scoring)". Labels: security, ai-ready.
   Body: reference GH #643 as prior instance, list 4 routes, cite route-security-guard-audit SKILL.md
   for implementation pattern.

2. **Add SUPABASE_ACCESS_TOKEN note block to ops/credential-rotation-schedule.md** — add:
   ### SUPABASE_ACCESS_TOKEN — Action Required
   - Last rotated: unknown — confirm in Supabase dashboard (Settings → API → Service Role Key)
   - Required for: brain connector (GH #394), KB autopopulate GH Action (GH #403), Supabase MCP
   - Human action: log the rotation date in the table after confirming with Supabase dashboard

---

## What This Replaces

Previous active direction: "Add SUPABASE_ACCESS_TOKEN to credential rotation schedule (run 104 winner)"
— partially implemented (row pre-existed; note block not added). Transitions to IMPLEMENTED status
with Bonus Action 2 above.

---

## Confidence: HIGH

Evidence base: 2 confirmed live instances (grep + GH issue), 3-cycle carry-forward governance mandate,
content verbatim from run 102, precedent at runs 99 + 101.
