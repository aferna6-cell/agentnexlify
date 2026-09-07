# Winning Concept — Run 118 (2026-09-07-pm)

## Recommendation

Create `.claude/skills/meter-ai-endpoint/SKILL.md` — a 6-step checklist skill that guides developers through the reserve/record/release metering lifecycle every time a new or unguarded AI endpoint is added or retrofitted.

## Why This, Why Now

9 metering commits landed in 7 days (#792–#803), each requiring 30–60 min and 400–1726 test lines of mechanical, error-prone work. Skill discovery 2026-09-07 rated `meter-ai-endpoint` HIGH priority and documented the exact pattern across 9 occurrences. Step 9L (now live per PR #804) detects unguarded functions and files GH issues — but gives no remediation guidance. Without a skill, each developer independently re-derives the 6-step pattern and re-hits the same mistakes: wrong import alias, missing release branch in exception handler, missing CI append. The skill closes the gap between detection (Step 9L → GH issue) and implementation (exact checklist). It also pairs with a bonus action: add a cross-reference in `ai-feature-pattern/SKILL.md` so metering guidance surfaces at authoring time, not just at audit time.

## Implementation Sketch

### Primary deliverable: `.claude/skills/meter-ai-endpoint/SKILL.md`

```markdown
---
name: meter-ai-endpoint
description: Reserve/record/release metering wrapper for any backend function calling Claude. Use when check_ai_metering.py reports a violation or when building a new AI endpoint.
version: 1.0.0
triggers:
  - meter <endpoint>
  - add usage guard
  - reserve/record/release
  - unmetered AI path
  - check_ai_metering reports violation
---

# Meter an AI Endpoint — Reserve / Record / Release

## Steps

### 1. Identify the call site
Run `python3 scripts/check_ai_metering.py` and read the `path:function:line` output.
Locate the function in `backend/routers/<path>.py` or `backend/services/<path>.py`.

### 2. Add imports
```python
from backend.services.ai_usage_guard import (
    reserve_ai_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    ai_usage_guard,
)
from backend.services.ai_usage_guard import estimate_widget_chat_tokens  # if token pre-estimate needed
```

### 3. Write `_load_<service>_budget_tenant(db, tenant_id)`
```python
def _load_<service>_budget_tenant(db, tenant_id: str):
    try:
        row = (
            db.table("tenants")
            .select("id, plan, ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit")
            .eq("id", tenant_id)
            .single()
            .execute()
        )
        return row.data if row.data else None
    except Exception:
        logger.warning("meter-ai: could not load tenant=%s", tenant_id)
        return None
```
Returns `None` on missing row or exception. Never logs PII.

### 4. Wrap the Claude call with the three-phase lifecycle
```python
async def my_endpoint(tenant_id: str, db = Depends(get_db)):
    tenant = _load_my_budget_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=503, detail="tenant unavailable")

    estimated = estimate_widget_chat_tokens(input_text)
    reservation = reserve_ai_tokens(db, tenant, estimated)
    if reservation is None:
        raise HTTPException(status_code=429, detail="AI budget exceeded")

    try:
        result = call_claude_messages(...)          # your AI call
        record_ai_usage(db, reservation, actual_tokens)
        return result
    except Exception:
        release_ai_token_reservation(db, reservation)
        raise
```

### 5. Write `backend/tests/test_<service>_usage_guard.py` — 4 required cases
- **Deny path:** budget exceeded → function returns 429 without calling Claude
- **Success path:** reservation recorded, Claude called exactly once
- **Failed record:** reservation released, no uncaught exception propagates
- **Missing tenant:** fails closed before provider (no Claude call, no reservation leak)

### 6. Append test file to CI
In `.github/workflows/pr-check.yml`, append `backend/tests/test_<service>_usage_guard.py` to the `-q` pytest command in "Run backend tests with coverage".

## Exemption
If a function genuinely should not be metered (e.g. admin-only internal tool, no tenant context), add `# ai-metering-exempt: <reason> : <ticket>` in the first 5 lines of the file. The detector will skip it. Requires a ticket reference.

## Verification
Run `python3 scripts/check_ai_metering.py` after implementation. Violation for the function should be gone. If not, re-check import aliases and guard detection pattern.
```

### Bonus action: Update `ai-feature-pattern/SKILL.md`

At the end of the "Standard Pattern" section, add:

> **Step 5. Metering (Required for all production AI paths)**
> Every function that calls Claude in production must use the reserve/record/release lifecycle.
> See the `meter-ai-endpoint` skill for the exact checklist. Unmetered paths are caught by `scripts/check_ai_metering.py` (Step 9L in nightly-commit-review).

## What This Replaces

No prior active direction replaced — additive. Complements Step 9L (detection) with a remediation checklist.

## Confidence

**HIGH** — Evidence is direct: 9 occurrences in one week, skill discovery explicit HIGH priority, pattern fully documented across real commits. No governance rejection precedent. Implementation sketch is complete and drawn from verified commit patterns.

## Run 119 Mandate

1. Verify `.claude/skills/meter-ai-endpoint/SKILL.md` exists (confirms human approved or nightly implemented).
2. Verify `ai-feature-pattern/SKILL.md` cross-reference added.
3. os_tool_executions.py: still 0 commits since f22ef04 (2026-09-03)? If 10d+ stable (≥2026-09-13): god class split is run 119 winner.
4. Step 9L: first nightly execution result — how many violations found? How many issues filed?
5. Step 9J token budget: which step before 9J consumes budget preventing full Dependabot coverage?
6. KB staleness: last compile 2026-08-26 (12 days). Did Step 9G trigger? Check knowledge-base/log.md.
