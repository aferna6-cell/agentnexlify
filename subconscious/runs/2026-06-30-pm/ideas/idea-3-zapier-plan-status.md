# Idea 3 — Zapier API Key Plan Status Enforcement (GH #107)

**Category:** Security / Revenue Protection
**Effort:** S (2-3 hours backend-only)
**Moratorium impact:** ADDS to human queue (requires_human: true) — BLOCKED by moratorium
**Evidence:**

- `docs/dev-knowledge/bug-patterns.md` — GH #107 open 61 days
- `backend/services/zapier_auth.py` — `_get_api_key_client()` resolves keys without `plan_status` check
- CLAUDE.md critical rules: `agent_os` ($99.99/mo) required for Zapier; `free` plan users must be gated
- Morning digest: no revenue-protection changes in 24h

## The Risk

`lapsed` or `cancelled` tenants can currently use Zapier integrations by keeping their API key. `_get_api_key_client` returns a valid client for any key in the DB, regardless of `plan_status`. Zero enforcement.

## Fix (confirmed from bug-patterns.md)

In `backend/services/zapier_auth.py`, `_get_api_key_client()`:
```python
# Add after key lookup:
if client.plan_status not in ('active', 'trialing'):
    raise HTTPException(status_code=402, detail="Subscription required")
```

## Why KILLED This Run

- Moratorium active: true_pending ~4, max 2. Adding this would push to ~5.
- 61 days open with no observed exploits cited in bug-patterns.md
- Already in parking lot with "route via issue-to-pr-loop" note
- Issue-to-pr-loop will pick this up when moratorium clears

## Parking Lot Note

Re-evaluate when true_pending_approvals drops to ≤1. Effort is S, risk is MEDIUM.
