# Idea 02: Zapier API Key Plan Status Security Fix (GH #107)

**Category:** code_health / security
**Effort:** S (1-2 hours — 3-line filter + regression test)
**ROI:** 2.5 (HIGH security, 57+ days open)
**Age:** GH #107 opened 2026-04-30 (57+ days as of run 70)
**Autonomous:** AUTONOMOUS-EXECUTABLE (LOW-risk auth check addition)

## Evidence

- `docs/dev-knowledge/bug-patterns.md`: "Zapier API key plan_status enforcement (GH #107, 2026-04-30): cancelled tenants bypass plan gate via `zapier_auth.py::_get_api_key_client`"
- `docs/dev-knowledge/customer-gaps.md`: Zapier plan_status listed as security bug open 57+ days
- GH #107 tagged security, open since 2026-04-30
- parking_lot entry: "Promote to first non-moratorium winner if #107 still open"
- NOT in rejected_paths — fully eligible

## What

In `backend/services/zapier_auth.py::_get_api_key_client`, the client lookup resolves API keys without checking `plan_status`. A tenant who cancels subscription but retains an unrevoked Zapier API key can continue using Zapier integrations indefinitely.

Fix: add `.in_(['active', 'trialing'])` filter on plan_status in the key resolution query.

```python
# before
result = db.from_("zapier_api_keys").select("*, clients(*)").eq("api_key", key).execute()

# after  
result = db.from_("zapier_api_keys").select("*, clients(*)").eq("api_key", key).in_("clients.plan_status", ["active", "trialing"]).execute()
```

Plus regression test: `test_cancelled_tenant_zapier_key_rejected`.

## Risk

- Query structure change — must confirm Supabase join filter syntax (`clients(plan_status)` vs nested filter)
- One new migration not required (filter only, no schema change)
- Risk of breaking active tenants if filter is wrong — needs careful query verification

## Debate Position

**STRONG candidate.** S-effort, HIGH security, 57+ days open, AUTONOMOUS-EXECUTABLE class. BUT: parking_lot note says "Route via issue-to-pr-loop, NOT subconscious winner queue." The issue is already tracked and tagged. Subconscious should nominate, not own the implementation.

**Weakness:** Could be executed by issue-to-pr-loop without needing a subconscious winner slot. Query filter syntax risk warrants schema-guardian review before execution.

**Verdict:** Recommend as WEAKENED → parking lot. Route to issue-to-pr-loop for GH #107. Not a subconscious winner — tracked separately.
