# Winning Concept — 2026-06-18-pm

**Title:** Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events  
**Category:** code_health  
**Confidence:** HIGH  
**Effort:** S (~20 min, 2 files, ~10 lines)  
**Autonomous-executable:** YES — nightly review path (MEDIUM-risk, sketch is complete)  
**Moratorium override:** YES — payment revenue bug (carry-over from run 59, still unimplemented)  

---

## Recommendation

Add `delete_key()` to `idempotency.py` and call it in the webhook exception handler in `stripe_webhooks.py` so Stripe retries can reprocess events that failed on first delivery.

## Why This, Why Now

`idempotency.py:check_and_record()` inserts the idempotency row BEFORE the handler runs. When the handler throws, `stripe_webhooks.py` raises `HTTPException(500)` (correct) but the row persists with `response_body=NULL`. On Stripe's retry, `check_and_record` finds the row, sees `response_body=NULL`, returns `(False, in_flight=True)` — the webhook handler short-circuits and returns 200 without processing the event. The event is permanently dropped. A tenant who fixes their payment card stays dunning-locked. This was introduced by `47c7f8b` (2026-06-16) and has been pending since run 59 (2026-06-17-pm). With 20+ commits/day velocity and active new-customer growth, any transient handler failure silently loses a payment event.

## Implementation Sketch

**File 1: `backend/services/idempotency.py`** — add after `record_response()`:

```python
async def delete_key(supabase, key: str) -> None:
    """Delete the idempotency row so the provider can retry.

    Call this inside an exception handler BEFORE re-raising.
    Allows Stripe / Twilio to retry the event on a fresh slate.
    """
    try:
        supabase.table("idempotency_keys").delete().eq("key", key).execute()
    except Exception:
        logger.exception("idempotency delete_key failed for key=%s — retry may be blocked", key)
```

**File 2: `backend/routers/stripe_webhooks.py`** — update the exception handler (~line 105):

```python
# Before:
except Exception:
    logger.exception("Stripe webhook handler failed for event %s", event_type)
    raise HTTPException(status_code=500, detail="Webhook handler failed")

# After:
except Exception:
    logger.exception("Stripe webhook handler failed for event %s", event_type)
    await delete_key(db, idempotency_key)  # allow Stripe retry on next delivery
    raise HTTPException(status_code=500, detail="Webhook handler failed")
```

Also add import at top: `from backend.services.idempotency import check_and_record, delete_key, record_response`

**File 3: `backend/tests/test_stripe_webhooks.py` (or new test file)** — regression test:

```python
def test_stripe_retry_processes_after_handler_failure():
    """Idempotency row deleted on handler exception; Stripe retry must process normally."""
    event_id = "evt_test_idempotency_308"
    idempotency_key = f"stripe:{event_id}"

    # First call: handler throws
    with patch_handler_to_raise(RuntimeError("simulated failure")):
        with pytest.raises(HTTPException) as exc_info:
            process_stripe_event(event_id, mock_checkout_payload)
        assert exc_info.value.status_code == 500

    # Idempotency row must be gone
    assert not idempotency_row_exists(idempotency_key)

    # Second call (Stripe retry): must process normally
    with patch_handler_to_succeed() as mock_handler:
        result = process_stripe_event(event_id, mock_checkout_payload)
        mock_handler.assert_called_once()
        assert result["status"] == "ok"
```

This test MUST FAIL on current HEAD (confirming bug) and PASS after fix.

## What This Replaces

Run 59 winner (same recommendation) — this run confirms the fix is still unimplemented and maintains the moratorium override.

## Confidence

**HIGH** — bug confirmed by direct code read. Fix is minimal (one new method, one await call, one import). Pattern is safe: delete-then-reraise is idiomatic for idempotent recovery. Regression test spec is fully written.

---

## Bonus A — Fix GH #292/#293 (do after main fix)

`sms_rate_limiter._UNLIMITED_PLANS` and `api_key_auth._ALLOWED_PLANS` still list old plan names (growth/autopilot/professional/enterprise). New `chatbot`/`agent_os` tenants can't use Zapier and get free-tier SMS limits. Fix: add `"chatbot"` and `"agent_os"` to each set. Proposed SMS limits: chatbot = 200/day, agent_os = 500/day. Also update `billing_reconciliation.py` plan caps. S-effort ~10 min.

## Bonus B — Add Plan-Name Guard to check_project_invariants (AUTONOMOUS-EXECUTABLE, after Bonus A)

Add check 7 to `scripts/check_project_invariants.py`: scan `sms_rate_limiter.py`, `api_key_auth.py`, `billing_reconciliation.py` for `chatbot` and `agent_os`. FAIL if either missing. ~15 lines Python. Prevents future repricing from silently breaking these files. Implement after Bonus A so the check passes on install.
