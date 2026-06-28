# Idea 02: Zapier plan_status Enforcement (GH #107)

**Category:** Code Health + Security  
**Effort:** ~2 hours  
**Priority:** MEDIUM

---

## The Problem

GitHub Issue #107 (open since Apr 30, 60+ days): Zapier API key authentication does not check `plan_status`. A tenant with an expired or cancelled subscription can continue using Zapier integrations indefinitely.

Current code path:
```python
# backend/services/zapier_auth.py
def _get_api_key_client(api_key: str) -> dict:
    # Validates api_key exists in DB
    # Returns client record
    # MISSING: plan_status check
```

A revoked or expired subscription should return 401/403. Currently returns 200.

---

## Evidence

- `docs/dev-knowledge/bug-patterns.md` — Zapier #107, "plan_status not checked", open since Apr 30
- Issue open 60+ days with no action
- Zapier is an `agent_os`-gated feature per CLAUDE.md plan gating rules
- `backend/tests/test_plan_gating_new_plans.py` — test file exists, new gate test should go here

---

## Recommended Fix

1 file change + 1 test:

```python
# backend/services/zapier_auth.py
def _get_api_key_client(api_key: str) -> dict:
    client = get_client_by_api_key(api_key)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if client.get("plan_status") not in ("active", "trialing"):
        raise HTTPException(status_code=403, detail="Subscription inactive")
    return client
```

Add test to `backend/tests/test_plan_gating_new_plans.py`:
- expired subscription → 403
- active subscription → 200
- no subscription → 403

---

## Risk

Low. Contained in `zapier_auth.py`. Only affects Zapier auth path. No migration needed.

---

## Why Not Winner

Smaller blast radius and lower customer-facing impact than SMS Dashboard. No new feature value. Bonus item to include alongside the winner.
