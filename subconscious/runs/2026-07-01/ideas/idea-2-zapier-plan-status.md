# Idea 2: Zapier API Key Plan_Status Enforcement (GH #107)

**Evidence:** `bug-patterns.md` documents this since 2026-04-30 (62 days). `backend/services/zapier_auth.py::_get_api_key_client` resolves API keys without checking `tenants.plan_status`. Cancelled/past-due tenants with non-revoked API keys still authenticate against Zapier endpoints. Revenue leakage + access control violation. Bug listed in run 74 backlog as parking-lot item (condition: true_pending ≤ 1). Moratorium override justified per precedents GH #308 + GH #292/#293 (both security/revenue bugs).

**Action:** Add `plan_status IN ('active','trialing')` check inside `_get_api_key_client` → return 402/403 for cancelled tenants. Add regression test: seed cancelled tenant + valid key → assert auth fails. 2 files: `backend/services/zapier_auth.py` + new test. AUTONOMOUS-EXECUTABLE — same class as nightly scope.

**Impact:** Closes 62-day revenue/access control gap. Prevents cancelled tenants from using Zapier integrations. Adds zero items to human queue (autonomous). Does NOT add to true_pending — clears a debt item. Precedent: runs 37, 52, 53 all implemented autonomously via nightly.

**Category:** code_health / security

**Moratorium override:** YES — security/revenue bug with 62-day window. Same class as GH #308 override (run 59).
