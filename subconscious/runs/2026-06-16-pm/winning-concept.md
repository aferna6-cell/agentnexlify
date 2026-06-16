# Winning Concept — 2026-06-16-pm (Run 59)

## Recommendation
Fix `backend/services/zapier_auth.py::_get_api_key_client` to check `plan_status IN ('active','trialing')` before resolving API keys — closes the revenue leak opened by the 7-day trial system launch.

## Why This, Why Now
The 7-day trial system launched on 2026-06-14/15 (PRs #299, #300, #301). pay_gate.py now gates web signup behind plan_status. But Zapier API key auth (`_get_api_key_client` in zapier_auth.py) has never checked plan_status — GH issue #107, filed 2026-04-30, in parking lot ROI 2.5 since run 16. Pre-trial, the gap was low-risk (active tenants had valid keys; cancelled tenants rarely set up Zapier). Post-trial, the vector is active: a trialing tenant can set up Zapier during their 7-day window, let the trial expire, and continue extracting leads, firing webhooks, and using API capacity indefinitely — pay_gate bypassed via the API layer. The fix is fully specified in bug-patterns.md (2-3 lines Python + one regression test) and is S-effort ~15 min. Parking lot note said "first non-moratorium winner" but was written before trials existed; time-sensitivity overrides the deferral.

## Implementation Sketch
1. Open `backend/services/zapier_auth.py`, find `_get_api_key_client` (around line where it queries `api_keys` table)
2. Add `plan_status IN ('active','trialing')` filter to the tenant query — join `tenants` table via `client_id` and assert `plan_status` is in allowed set
3. On failed check: return `None` or raise 402/403 (consistent with how the rest of auth fails)
4. Add regression test in `backend/tests/test_zapier_auth.py`:
   - Seed: cancelled tenant with a valid (un-revoked) API key
   - Assert: `_get_api_key_client(key)` returns `None` / raises 402
   - Assert: active tenant with same key → succeeds
   - Assert: trialing tenant with same key → succeeds
5. Wire test into `pr-check.yml` (or it's already there if test file exists)
6. Close GH #107

## Bonus Action (tonight, autonomous)
Check 13 (wire `check_project_invariants.py` into pre-commit as FAIL gate) is queued via pending_autonomous. Nightly at 2:37 AM should execute it automatically. Verify in tomorrow's git log.

## What This Replaces
Parking lot entry "Zapier API key plan_status enforcement" (added run 16, ROI 2.5, note: "promote to first non-moratorium winner if #107 still open"). Overriding deferral on time-sensitivity grounds — 7-day trials create active revenue leak vector that didn't exist at run 16.

## Confidence
HIGH — fix is fully specified in bug-patterns.md, implementation path is clear, S-effort ~15 min, zero unknown dependencies, regression test pattern is standard.
