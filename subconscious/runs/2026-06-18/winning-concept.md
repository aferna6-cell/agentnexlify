# Winning Concept — Run 2026-06-18

**Title:** Fix plan-name access dicts — sms_rate_limiter.py + api_key_auth.py (GH #292/#293 scope)
**Category:** code_health
**Confidence:** HIGH
**Effort:** S (~15 min, 2 files, ~4 lines changed)
**Autonomous-executable:** NO — access/billing code requires human review (feature-access regression for paying customers)
**Moratorium override:** YES — broken core features for 100% of new paid tenants = direct churn risk

---

## Problem

The June 15 repricing introduced two paid plan names: `chatbot` ($19.99/mo) and `agent_os` ($99.99/mo). Four backend files still reference only the retired plan names. Two confirmed live feature-access bugs:

### Bug 1 — SMS rate limiting (sms_rate_limiter.py:10)

```python
_UNLIMITED_PLANS = {"growth", "professional", "autopilot", "enterprise"}
FREE_DAILY_LIMIT = 50
```

`agent_os` and `chatbot` are not in `_UNLIMITED_PLANS`. `check_sms_rate_limit()` returns `True` only for plans in that set; everything else gets capped at 50 SMS/day. Every new paid tenant is at the free-tier SMS limit. Agent_os at $99.99/mo should have unlimited or high SMS.

### Bug 2 — API key / Zapier access (api_key_auth.py:29)

```python
_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}
```

`chatbot` and `agent_os` are not in `_ALLOWED_PLANS`. Any gate that calls this denies Zapier integration to ALL new paid tenants. Zapier is a core integration for the chatbot tier (lead routing, CRM sync).

---

## Fix

### sms_rate_limiter.py

```python
# Before:
_UNLIMITED_PLANS = {"growth", "professional", "autopilot", "enterprise"}
FREE_DAILY_LIMIT = 50

# After:
_UNLIMITED_PLANS = {"agent_os"}          # premium tier: unlimited
_CHATBOT_DAILY_LIMIT = 200               # chatbot tier: 200/day (generous but metered)
FREE_DAILY_LIMIT = 50                    # free/unknown: 50/day
```

Update `check_sms_rate_limit()` to use a 3-tier check:

```python
def check_sms_rate_limit(tenant_id: str, plan: str) -> bool:
    _maybe_reset()
    if plan in _UNLIMITED_PLANS:
        return True
    daily_limit = _CHATBOT_DAILY_LIMIT if plan == "chatbot" else FREE_DAILY_LIMIT
    return _daily_sms.get(tenant_id, 0) < daily_limit
```

**Note on product decision:** 200/day for chatbot is conservative (one real business can send 200 SMS/day easily). If product owner wants unlimited for chatbot too, simply add `"chatbot"` to `_UNLIMITED_PLANS`. The critical fix is that `agent_os` gets unlimited now.

### api_key_auth.py

```python
# Before:
_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}

# After:
_ALLOWED_PLANS = {"chatbot", "agent_os"}
```

Both paid plans can use API keys and Zapier integration. This is correct — both are paid tiers with Zapier listed as a feature.

---

## Bonus A — Fix billing_reconciliation.py + orchestrator.py (complete GH #292/#293)

### billing_reconciliation.py:33-49

`_PLAN_AGENT_RUN_CAPS` and `_PLAN_BASELINE_AI_TOKENS` have only old plan names. New tenants get no match → wrong caps/baselines. Requires product decision on values.

Proposed values (conservative, can be tuned):
```python
_PLAN_AGENT_RUN_CAPS: dict[str, int] = {
    "chatbot": 200,       # AI Front Desk equivalent of legacy growth
    "agent_os": 1500,     # AI Workforce equivalent of legacy professional
    "free": 25,           # keep for legacy free tenants
}

_PLAN_BASELINE_AI_TOKENS: dict[str, int] = {
    "chatbot": 1_000_000,   # same as legacy growth
    "agent_os": 2_000_000,  # same as legacy professional
    "free": 150_000,
}
```

### orchestrator.py:238/319

```python
# Before:
if plan in ("professional", "enterprise"):
    # send branded email

# After:
if plan in ("agent_os",):
    # send branded email
```

Agent_os is the new premium tier. Branded email is appropriate for it. Chatbot tier gets standard email (same as old growth/autopilot).

---

## Bonus B — Add Check 7 to check_project_invariants.py (AUTONOMOUS-EXECUTABLE)

After Bonus A lands, add Check 7: scan `sms_rate_limiter.py`, `api_key_auth.py`, `billing_reconciliation.py` for current plan names (`chatbot`, `agent_os`). FAIL if any missing.

This prevents every future repricing from silently breaking feature access.

---

## Regression Tests

Add to `backend/tests/test_sms_rate_limiter.py`:

```python
def test_agent_os_plan_has_unlimited_sms():
    assert check_sms_rate_limit("tenant-1", "agent_os") is True

def test_chatbot_plan_has_200_per_day_limit():
    for _ in range(200):
        increment_sms_count("tenant-2")
    assert check_sms_rate_limit("tenant-2", "chatbot") is False  # at limit
    # Should pass for agent_os at same count:
    for _ in range(200):
        increment_sms_count("tenant-3")
    assert check_sms_rate_limit("tenant-3", "agent_os") is True
```

Add to `backend/tests/test_api_key_auth.py`:

```python
def test_chatbot_plan_can_create_api_key():
    assert is_plan_allowed_api_key("chatbot") is True

def test_agent_os_plan_can_create_api_key():
    assert is_plan_allowed_api_key("agent_os") is True
```

These tests must FAIL on current HEAD (proving the bug) and PASS after the fix.

---

## Implementation Path

1. Update `sms_rate_limiter.py` — 3-tier check logic (5 lines)
2. Update `api_key_auth.py` — replace set (1 line)
3. Add regression tests for both
4. Commit + push → PR
5. Bonus A: fix `billing_reconciliation.py` + `orchestrator.py` in same PR
6. Bonus B: Add Check 7 to `check_project_invariants.py` (AUTONOMOUS-EXECUTABLE)

---

## What This Replaces

Run 59 winner (GH #308 idempotency early-write) was the previous active direction. GH #308 remains a standing action — the implementation sketch is in `subconscious/runs/2026-06-17-pm/winning-concept.md` and the nightly review path is authorized. GH #308 is not abandoned — it's been handed to nightly review. This run promotes GH #292/#293 to main winner based on broader immediate customer impact (100% of new paid tenants vs. low-probability payment recovery path).
