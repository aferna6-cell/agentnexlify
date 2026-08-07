# Winning Concept — 2026-08-07-pm (Run 103)

## Recommendation
Add plan gating, demo guard, and AI usage guard to `backend/routers/appointment_briefs.py` and `backend/services/appointment_brief.py`. The appointment brief feature (pre-meeting brief + follow-up draft generator) shipped 2026-08-06 in `e0e9be6` with two Claude Sonnet 5 calls and zero access controls beyond authentication.

**Escalation status: RECOMMENDATION — code change, S effort. Route to issue-to-pr-loop via GH issue.**

## Why This, Why Now

`appointment_brief.py` calls `call_claude_messages` twice (lines 119, 150) with `BRIEF_MODEL = "claude-sonnet-5"`. The `appointment_briefs.py` router authenticates via `_get_current_tenant` only — no `block_demo_role`, no plan feature gate, no `ai_usage_guard`.

Three layers of control are ALL missing:
1. **Demo guard** — demo-role tenants can trigger LLM calls (same issue as buy-usage, fixed yesterday)
2. **Plan gate** — appointment briefs are an agent_os feature (appointment intelligence); chatbot-tier tenants should not access them
3. **Usage guard** — no token/usage cap, no per-plan quota enforcement

This is the same class of issue the nightly caught and fixed immediately on `billing_usage.py::buy-usage` (2026-08-07, commit `cbbaae5`). That endpoint was missing only `block_demo_role`. `appointment_briefs.py` is missing all three guards.

**Evidence:**
- `appointment_brief.py`: `from backend.services.llm_runtime import call_claude_messages` + `BRIEF_MODEL = "claude-sonnet-5"`. Lines 119, 150: `resp = await call_claude_messages(...)`.
- `appointment_briefs.py` router: grep for ai_usage_guard/check_usage/plan_check/block_demo → **zero results**. Only guard: `Depends(_get_current_tenant)`.
- `billing_usage.py` fix pattern: `from backend.dependencies import block_demo_role` + `dependencies=[Depends(block_demo_role)]` on route decorator.

## Verbatim Fix Specification

### File 1: `backend/routers/appointment_briefs.py`

**Add import (after existing imports):**
```python
from backend.dependencies import block_demo_role, verify_tenant
from backend.services.ai_usage_guard import get_ai_usage_status, PLAN_FEATURES
```

**Add to router-level or per-route dependencies:**
```python
# On each route that calls appointment_brief service:
@router.get("/briefs/{appointment_id}", dependencies=[Depends(block_demo_role), Depends(verify_tenant)])
@router.post("/follow-up/{appointment_id}", dependencies=[Depends(block_demo_role), Depends(verify_tenant)])
```

**Add plan feature gate inside each endpoint:**
```python
async def get_appointment_brief(
    appointment_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    # Plan gate: appointment briefs are agent_os feature
    plan = claims.get("plan", "free")
    if plan not in PLAN_FEATURES.get("appointment_briefs", ["agent_os", "growth", "autopilot", "professional", "enterprise"]):
        raise HTTPException(status_code=403, detail="Appointment briefs require agent_os plan")
    ...
```

### File 2: `backend/services/appointment_brief.py`

No service-level changes needed if router guards are applied correctly — the service is called only from the guarded router. If service is called from other paths, add plan check at service entry:
```python
# Optional defensive check at service layer
async def generate_brief(..., plan: str = "free") -> dict:
    if plan not in ["agent_os", "growth", "autopilot", "professional", "enterprise"]:
        return {"error": "Appointment briefs require agent_os plan"}
    ...
```

## Implementation Path

1. File GH issue: "MEDIUM: appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard — same class as buy-usage fix (cbbaae5)"
2. Labels: `security`, `medium-risk`, `nightly-review`, `ai-ready`
3. Route via issue-to-pr-loop for automated implementation
4. Test gate: add test to `backend/tests/test_plan_gating_new_plans.py` verifying chatbot-plan tenant gets 403 on appointment brief endpoints

## What This Closes

Same pattern as `block_demo_role` on `buy-usage` caught by nightly yesterday. Nightly does not currently check for plan gating on new LLM-calling services — this finding comes from subconscious evidence sweep, not the automated check.

**Bonus action (not autonomous):** Add a Step 9E-class check to nightly SKILL.md: scan new `backend/services/*.py` files for `call_claude_messages` without a corresponding `ai_usage_guard` or plan gate reference. Would have caught this before shipping.

## Confidence
**HIGH** — Confirmed via grep. Same class as yesterday's fix. Fix pattern exists in `billing_usage.py`. S effort (2 files, 3 dependency lines, 1 plan gate, 1 test). GH issue → issue-to-pr-loop channel → reviewed PR.
