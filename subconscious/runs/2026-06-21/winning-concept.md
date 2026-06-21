# Winning Concept — 2026-06-21 (Run 65)

## Recommendation

Fix GH #308 — add `async def delete_key()` to `backend/services/idempotency.py` and call it in the `stripe_webhooks.py` exception handler before re-raising, so failed webhook handlers don't permanently drop Stripe payment events.

## Why This, Why Now

Run 65 mandate fires per `subconscious/runs/2026-06-20-pm/winning-concept.md` §RUN 65 MANDATE: GH #292/#293 confirmed still unimplemented (grep today: `chatbot`/`agent_os` absent from `sms_rate_limiter._UNLIMITED_PLANS` and `api_key_auth._ALLOWED_PLANS`) — alternating mandate switches winner back to GH #308. Beyond mandate compliance, this is a data-loss class revenue bug: `check_and_record()` in `idempotency.py` inserts the idempotency row at line 44-52 BEFORE the handler completes. Any exception in the Stripe handler leaves the row with `response_body=NULL`. On retry, `is_new=False` → the webhook router returns 200 without processing → the event is permanently dropped. Tenants who fix their payment card stay dunning-locked with no recourse. GH #308 has been open since 2026-06-17 (5 days) and unimplemented across 7 consecutive subconscious cycles (runs 59-65). The fix is ~10 lines with a complete sketch documented since run 59.

## Implementation Sketch

1. **Add `delete_key()` to `backend/services/idempotency.py`** (after `record_response` function, ~line 113):
   ```python
   async def delete_key(supabase, key: str) -> None:
       """Delete an idempotency row so a failed handler can be retried.

       Call this in the exception handler before re-raising so Stripe retries
       are processed rather than short-circuited as duplicates.
       """
       try:
           supabase.table("idempotency_keys").delete().eq("key", key).execute()
       except Exception:
           logger.exception("idempotency delete_key failed for key=%s", key)
   ```

2. **Update `backend/routers/stripe_webhooks.py` exception handler** — find the `except Exception` / `except HTTPException` block that re-raises after handler failure. Before the re-raise, add:
   ```python
   await delete_key(db, idempotency_key)
   ```
   Import `delete_key` from `backend.services.idempotency` at the top of the file.

3. **Write regression test** in `backend/tests/test_stripe_idempotency.py` (or existing test file):
   - Test MUST fail on HEAD (idempotency row persists after simulated handler exception)
   - Test MUST pass after fix (delete_key removes row; second call to check_and_record returns `is_new=True`)
   - Mock: use `unittest.mock.patch` on `supabase.table` to avoid real DB calls

4. **Verify**: `grep -n "delete_key" backend/services/idempotency.py` should return the new method. `grep -n "delete_key" backend/routers/stripe_webhooks.py` should return the callsite.

## Bonus A — Fix GH #292/#293 (~20 min, human required)

Wire `chatbot` and `agent_os` into plan-name dicts. Full sketch: `subconscious/runs/2026-06-19-pm/winning-concept.md`.

Files:
- `backend/services/sms_rate_limiter.py` line ~10: add `chatbot`, `agent_os` to `_UNLIMITED_PLANS`
- `backend/routers/api_key_auth.py` line ~29: add to `_ALLOWED_PLANS`
- `backend/services/billing_reconciliation.py` lines ~33-50: add cap entries for both plans

Confirm SMS limit for `chatbot` before merging (proposed: unlimited, same as growth tier).

## Bonus B — Plan-Name Guard Check 7 (AUTONOMOUS-EXECUTABLE after Bonus A lands)

Add Check 7 to `scripts/check_project_invariants.py` — validate both `chatbot` and `agent_os` appear in `sms_rate_limiter._UNLIMITED_PLANS` and `api_key_auth._ALLOWED_PLANS`. Prevents future repricing from silently omitting new plan names at pre-commit.

## What This Replaces

Previous winner: Fix GH #292/#293 (run 64, mandate). GH #292/#293 is demoted to Bonus A this run per mandate alternation. It remains the second-highest-priority open bug and should be fixed alongside or immediately after GH #308.

## RUN 66 MANDATE

If GH #308 still unimplemented by run 66: switch winner to GH #292/#293 (alternating mandate continues). Sketch: `subconscious/runs/2026-06-19-pm/winning-concept.md`.

## Confidence

HIGH — mandate compliance + confirmed bug (direct code read) + complete implementation sketch + regression test spec included + no new blockers identified.
