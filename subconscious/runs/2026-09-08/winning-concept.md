# Winning Concept — Run 118 (2026-09-08)

## Recommendation

Create `.claude/skills/meter-ai-endpoint/SKILL.md` — a 6-step skill that automates the reserve/record/release metering lifecycle for any unguarded AI-calling function detected by `scripts/check_ai_metering.py`.

## Why This, Why Now

Step 9L shipped (PR #804, 2026-09-07) and its live scan confirms 30+ unguarded AI-calling functions across 16 router files and 14 service files. The issue-to-pr-loop is stalled (GH #399, AUTOPILOT_GH_TOKEN expired) — Step 9L issues won't auto-fix. Each violation requires 30-60 minutes of manual work: importing the right functions, writing the `_load_budget_tenant` helper, wrapping the call in the 3-phase lifecycle, writing 4 required test cases, and adding the test file to CI. The same 6-step pattern appeared in 9 commits this week (commits bc0332b → c2e5864), making it the highest-signal repeated pattern in the skill discovery report. Packaging it as a skill drops per-endpoint time to ~10 minutes and prevents the next emergency metering sprint.

## Implementation Sketch

Create `.claude/skills/meter-ai-endpoint/SKILL.md` with the following structure:

```markdown
---
name: meter-ai-endpoint
description: Add AI usage guard (reserve/record/release) to an unguarded AI-calling function. Use when check_ai_metering.py reports a violation or when adding a new Claude API call.
version: 1.0.0
origin: subconscious-run-118
user-invocable: true
triggers:
- meter endpoint
- add usage guard
- reserve record release
- unmetered AI
- check_ai_metering violation
effort: medium
---

# meter-ai-endpoint — Billing Lifecycle Wrapper

Use when `scripts/check_ai_metering.py` reports a violation (`path:function:line`) or when adding a new Claude API call to ensure it participates in tenant billing accounting.

## Step 1: Locate the violation

Run the detector if you don't have a specific target:
```bash
python3 scripts/check_ai_metering.py
```
Output format: `path:function:line`. Pick one violation. Read the file to understand the function's existing signature and call context.

## Step 2: Add imports

At the top of the file (after existing imports), add:
```python
from backend.services.ai_usage_guard import (
    reserve_ai_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    estimate_widget_chat_tokens,   # if estimating from text
)
```

If the function is a FastAPI route handler AND the function is interactive (user-facing), add to its parameter defaults:
```python
_: None = Depends(ai_usage_guard)
```
Import `ai_usage_guard` from `backend.dependencies` (check existing imports in the router for the exact path).

## Step 3: Write `_load_<service>_budget_tenant`

Add a private helper in the same file (before the function):
```python
async def _load_{service}_budget_tenant(db, tenant_id: str):
    try:
        row = (
            await db.table("tenants")
            .select("id, plan, ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit")
            .eq("id", tenant_id)
            .single()
            .execute()
        )
        return row.data
    except Exception:
        logger.warning("meter-ai: tenant load failed", extra={"tenant": tenant_id})
        return None
```

Note: `tenant_id` here is the tenant UUID (`tenants.id`), NOT `client_id` from the `leads` table. These are different columns.

## Step 4: Wrap the Claude call with 3-phase lifecycle

Replace the bare `call_claude_messages(...)` (or `client.messages.create(...)`) with:
```python
tenant = await _load_{service}_budget_tenant(db, tenant_id)
if tenant is None:
    # Fail closed — no metering data means no AI call
    return default_response_or_raise

estimated = estimate_widget_chat_tokens(prompt_text)  # or a hardcoded estimate
reservation = await reserve_ai_tokens(db, tenant, estimated)
if reservation is None:
    return budget_exceeded_response

try:
    result = await call_claude_messages(...)
    actual = result.usage.input_tokens + result.usage.output_tokens
    await record_ai_usage(db, reservation, actual)
    return result
except Exception:
    await release_ai_token_reservation(db, reservation)
    raise
```

## Step 5: Write 4 required test cases

Create `backend/tests/test_{service}_usage_guard.py` with these exact 4 cases:
1. **Budget denial** — reserve returns None → function returns early, Claude NOT called
2. **Success** — reservation recorded, Claude called exactly once, return value correct
3. **Failed record** — `record_ai_usage` raises → reservation released, no uncaught exception propagates
4. **Missing tenant** — `_load_budget_tenant` returns None → fails closed before Claude call

Reference `backend/tests/test_widget_guard.py` for fixtures and patterns.

## Step 6: Add to CI

In `.github/workflows/pr-check.yml`, find the `pytest` line in "Run backend tests with coverage" and append:
```
backend/tests/test_{service}_usage_guard.py
```

## Verify

```bash
python3 scripts/check_ai_metering.py | grep {function}
# Should no longer appear in output
python3 -m pytest backend/tests/test_{service}_usage_guard.py -v
```

## Reference implementations (read before starting)
- `backend/services/bot_health.py` — service-level pattern
- `backend/routers/widget_chat.py` — router-level pattern (Depends approach)
- `backend/tests/test_widget_guard.py` — test fixture patterns
```

## What This Replaces

No prior active direction replaced. Step 9L (AI metering sweep) continues to detect violations nightly. This skill is the remediation layer for what Step 9L detects.

## Confidence

**HIGH** — Pattern repeated 9 times this week in confirmed commits. Skill discovery 2026-09-07 independently proposed this exact skill with matching steps and estimated savings. Implementation sketch maps directly to 9 evidence commits. No dependency on stalled systems (GH #399, GH #403). XS-effort to create the SKILL.md; medium-effort per endpoint to apply it.
