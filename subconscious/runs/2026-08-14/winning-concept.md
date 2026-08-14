# Run 106 — Winning Concept (2026-08-14)

## Fix `backend/routers/appointment_briefs.py` — add `block_demo_role` router guard + structural test

**Category:** code_health / security
**Effort:** XS (~10 min)
**Confidence:** HIGH
**Status:** EXECUTED — applied directly in this run

---

## Problem

`appointment_briefs.py` has two POST endpoints:
- `/{tenant_id}/{appointment_id}/brief` — calls `appointment_brief.generate_brief()` → Claude API
- `/{tenant_id}/{appointment_id}/follow-up-draft` — calls `appointment_brief.draft_followup()` → Claude API

Both endpoints are missing `block_demo_role` guard. Demo tenants can reach these endpoints and consume AI tokens to generate appointment briefs and follow-up drafts without any quota enforcement. This is a security + cost gap.

GH #643 has been open 7 days, labeled `ai-ready` + `security` + `medium-risk`. AUTOPILOT_GH_TOKEN expired (#399) prevents the standard autopilot-issue-loop from fixing it. Nightly-commit-review operates on `main`; PR #653 is unmerged, so nightly cannot apply the fix from this branch. Run 105 cleared AUTONOMOUS-EXECUTABLE twice.

---

## Fix Applied

### `backend/routers/appointment_briefs.py`

**Before:**
```python
from backend.dependencies import _get_current_tenant
...
router = APIRouter(prefix="/api/v1/appointments", tags=["appointment-briefs"])
```

**After:**
```python
from backend.dependencies import _get_current_tenant, block_demo_role
...
router = APIRouter(
    prefix="/api/v1/appointments",
    tags=["appointment-briefs"],
    dependencies=[Depends(block_demo_role)],
)
```

Canonical reference: `backend/routers/billing.py` — router-level `dependencies=[Depends(block_demo_role)]` (lines 1-8). This is the established pattern for all billing/AI-consumption endpoints.

### `backend/tests/test_plan_gating_new_plans.py`

Added `test_appointment_briefs_router_has_block_demo_role_guard()`:
- Imports `router` from `appointment_briefs`
- Checks `router.dependencies` for `block_demo_role`
- Fails with explicit message if guard is missing or silently removed

---

## What was NOT done (follow-up scope)

- **ai_usage_guard / plan gate**: `reserve_ai_tokens()` requires a full tenant dict (with `plan`, `ai_monthly_token_alert_threshold`, `ai_monthly_token_hard_limit`). The router currently only has `tenant_id` (string from path). Adding the guard would require a DB round-trip to fetch the full tenant row, which exceeds XS scope and adds latency to every request. Follow-up: add `reserve_ai_tokens` call in `appointment_brief.generate_brief()` service where the Claude call actually lives.

---

## Evidence Chain

- `backend/routers/appointment_briefs.py` — grep confirmed: `block_demo_role` absent before this fix
- `billing.py:1-8` — canonical router-level guard pattern
- `billing_usage.py:c204af2 (2026-08-08)` — same fix applied 6 days ago
- GH #643 — open 7 days, ai-ready + security labels, no linked PR
- nightly-2026-08-13 Step 9D — confirmed #643 as top open blocker
- `.claude/skills/route-security-guard-audit/SKILL.md` — run 104 created exact execution guide

---

## Bonus Actions (same run)

### Bonus A: Governance reconciliation
- `total_runs`: 105 → 106 (4 branch runs 103-105 never updated state)
- `last_run`: "2026-08-13-pm" → "2026-08-14"
- `run_107_mandate` added

### Bonus B: Step 9E threshold 76d → 45d
- File: `.claude/skills/nightly-commit-review/SKILL.md`
- Current AUTOPILOT_GH_TOKEN: 41d since rotation — no alert fires at 76d threshold
- 45d would have triggered Day-4 warning, giving human 4 days advance notice
- Prior incident: AUTOPILOT_GH_TOKEN and brain connector PAT both expired same day 2026-07-04 with no advance warning

---

## Canonical References
- `backend/routers/billing.py:1-8` — router-level block_demo_role pattern
- `backend/tests/test_plan_gating_new_plans.py:test_buy_usage_has_block_demo_role_guard` — existing structural test shape
- `.claude/skills/route-security-guard-audit/SKILL.md` — audit skill
- GH #643 — originating issue
