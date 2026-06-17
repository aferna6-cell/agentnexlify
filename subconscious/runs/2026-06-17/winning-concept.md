# Winning Concept — 2026-06-17

## Recommendation
Fix the webhook idempotency retry-drop bug in billing.py and stripe_webhooks.py: change `if not is_new` to `if not is_new and _cached is not None` so a failed handler doesn't permanently suppress Stripe's retries — AUTONOMOUS-EXECUTABLE.

## Why This, Why Now
PR #301 (47c7f8b, 3 days ago) shipped dunning recovery — `_handle_payment_succeeded` now rescues paused tenants whose card was charged successfully. The idempotency guard has a silent failure mode: `check_and_record` inserts the idempotency key before the handler runs; if the handler raises an exception (DB hiccup, Supabase cold start), the 500 response triggers Stripe's retry mechanism — but on retry, `check_and_record` returns `(False, None)` and the current code returns `{"status": "ok"}` without processing, permanently dropping the event. The nightly review filed GH #308 today with MEDIUM severity. This is moratorium-exempt (code defect, not new feature), AUTONOMOUS-EXECUTABLE, and directly relevant to the active billing focus.

## Implementation Sketch
1. **billing.py** — find line ~235:
   ```python
   is_new, _cached = await check_and_record(db, "stripe", event_id)
   if not is_new:
       logger.info("Stripe duplicate event %s — skipping reprocess", event_id)
       return {"status": "ok"}
   ```
   Replace with:
   ```python
   is_new, _cached = await check_and_record(db, "stripe", event_id)
   if not is_new and _cached is not None:
       logger.info("Stripe duplicate event %s — skipping reprocess", event_id)
       return {"status": "ok"}
   elif not is_new:
       logger.warning(
           "Stripe event %s: idempotency key exists but no response stored "
           "(prior handler failed) — reprocessing", event_id
       )
   ```

2. **stripe_webhooks.py** — apply the same change to the duplicate check in `stripe_webhook()` (same pattern, same bug).

3. **Test**: Add test to `backend/tests/test_conversion_funnel.py` or create `backend/tests/test_billing_idempotency.py`:
   - Simulate `invoice.payment_succeeded` handler raising on first call
   - Assert `check_and_record` returns `(False, None)` on retry
   - Assert handler IS called on retry (not short-circuited)
   - Assert tenant `plan_status` is updated to `active`

4. Verify `record_response` is called on success path (already at billing.py:285).

5. Close GH #308.

## What This Replaces
Active direction from run 58 (Check 13 wired). Run 58 is now `implemented`. This is the first post-Check-13 improvement: the invariant gate is in place, now fixing the billing reliability bug the gate would have missed (behavioral, not structural).

## Governance Notes (apply in Phase 6)
- **Run 58** (`Wire check_project_invariants.py into pre-commit as Check 13`): `pending_autonomous` → `implemented` (bc91e97, 2026-06-17, nightly review)
- **runs_implemented**: 18 → 19

## Confidence
HIGH — code path verified in billing.py:234-285, bug mechanism confirmed by inspection, fix is 8 lines in 2 files, no schema change, test pattern clear, AUTONOMOUS-EXECUTABLE.
