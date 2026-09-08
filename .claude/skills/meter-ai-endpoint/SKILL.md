---
name: meter-ai-endpoint
description: "Use this skill when adding or retrofitting AI usage metering around production Claude calls. Applies the reserve/record/release lifecycle, fail-closed tenant budget loading, required tests, and CI wiring used by Agent Nexlify's ai_usage_guard."
version: 1.0.0
origin: chatgpt
allowed-tools: []
disable-model-invocation: true
triggers: ["meter endpoint", "meter function", "add usage guard", "reserve/record/release", "unmetered AI path", "check_ai_metering.py", "AI usage guard"]
effort: medium
---

# Meter AI Endpoint

## When to Use
Use this skill when a backend production path calls `call_claude_messages`, `call_claude_messages_sync`, or `anthropic.Anthropic().messages.create()` and needs billing/usage metering.

Typical triggers:
- "meter `<function>`"
- "add usage guard to `<service>`"
- "reserve/record/release for `<endpoint>`"
- "unmetered AI path"
- `scripts/check_ai_metering.py` reports a violation

For prompt engineering and response parsing, use `ai-feature-pattern` alongside this skill.

## Canonical Lifecycle

### 1. Identify the exact provider call
Start from the scanner finding (`path:function:line`) or locate the Claude call directly. Meter the function that owns the provider call rather than a distant caller.

Legitimate exceptions must use the scanner's explicit exemption marker:

```python
# ai-metering-exempt: <reason> : <ticket>
```

Do not add an exemption just to silence CI.

### 2. Import the usage guard primitives
Use the canonical helpers from `backend.services.ai_usage_guard`:

```python
from backend.services.ai_usage_guard import (
    estimate_widget_chat_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    reserve_ai_tokens,
)
```

Use the estimator that matches the path when a more specific estimator already exists. Do not invent a second metering subsystem.

### 3. Load the budget tenant and fail closed
Add a small service-local helper such as `_load_<service>_budget_tenant(db, tenant_id)` that selects only the fields required by the usage guard:

```text
id, plan, ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit
```

Requirements:
- Return `None` when the tenant row is missing.
- Return `None` on database/read exceptions.
- Log the failure with `tenant=<id>` and no customer PII.
- The caller must fail closed before the provider call when the helper returns `None`.

### 4. Reserve before calling Claude
Estimate the request cost, then reserve against the tenant budget before any provider call:

```python
tenant = _load_service_budget_tenant(db, tenant_id)
if tenant is None:
    return None  # or the service's documented safe fallback

estimated_tokens = estimate_widget_chat_tokens(...)
reservation = reserve_ai_tokens(
    db=db,
    tenant=tenant,
    estimated_tokens=estimated_tokens,
)
if reservation is None:
    return None  # budget denial: provider must not be called
```

Preserve the function's existing return contract when choosing the safe fallback.

### 5. Record on success; release on failure
Wrap the provider call so every successful reservation reaches exactly one terminal state:

```python
reservation = reserve_ai_tokens(...)
if reservation is None:
    return None

try:
    response = call_claude_messages_sync(...)
    actual_tokens = ...  # derive from the canonical response usage metadata
    record_ai_usage(
        db=db,
        reservation=reservation,
        actual_tokens=actual_tokens,
    )
    return response
except Exception:
    release_ai_token_reservation(db=db, reservation=reservation)
    raise
```

If the service intentionally swallows provider exceptions (for example a background best-effort path), keep that behavior, but still release the reservation before returning the fallback.

A reservation must never be left outstanding after a provider or recording failure.

## Required Tests
Create `backend/tests/test_<service>_usage_guard.py` with at least these four cases:

1. **Budget denial** — reserve is denied; provider is not called.
2. **Success** — reservation is created, provider is called exactly once, usage is recorded.
3. **Failure after reservation** — provider or record path fails; reservation is released and the service preserves its documented error/fallback behavior.
4. **Missing tenant** — tenant lookup fails closed before reserve/provider execution.

Prefer asserting lifecycle behavior over exact implementation details.

## CI Wiring
Agent Nexlify's PR validation currently uses an explicit backend pytest file list. Add the new usage-guard test file to the `Run backend tests with coverage` command in `.github/workflows/pr-check.yml` unless the workflow has since been migrated to test discovery.

Before editing that workflow, inspect the current command; do not duplicate an existing test entry.

## Validation
Run or require evidence for:

```text
python scripts/check_ai_metering.py
pytest backend/tests/test_<service>_usage_guard.py
full PR Validation
```

The lane is not complete merely because unit tests pass; the scanner must also stop reporting the unmetered production call.

## Checklist
- [ ] Metering surrounds the function that actually calls the AI provider
- [ ] Tenant budget row is loaded with only required fields
- [ ] Missing/error tenant lookup fails closed before provider execution
- [ ] Tokens are reserved before the provider call
- [ ] Budget denial prevents the provider call
- [ ] Successful calls record actual usage
- [ ] Provider/record failures release the reservation
- [ ] No PII is added to usage-guard logs
- [ ] Four lifecycle tests cover denial, success, failure/release, and missing tenant
- [ ] `scripts/check_ai_metering.py` passes for the changed path
- [ ] New test is included in PR validation if the workflow still uses an explicit list

## Gotchas
- **Reserve after the provider call defeats the guard.** The provider must never run before reservation succeeds.
- **Fail-open tenant lookup creates unbilled AI usage.** Missing tenant/budget state must stop the provider path.
- **Recording is not the same as releasing.** A failed provider call cannot be recorded as normal usage; release its reservation.
- **Exception-swallowing background jobs still need release.** Preserve the best-effort contract only after cleanup.
- **Do not blindly use `estimate_widget_chat_tokens`.** Reuse a path-specific estimator when one already exists.
- **Scanner exemptions require a reason and ticket.** They are for legitimate internal/non-billable paths, not implementation shortcuts.
