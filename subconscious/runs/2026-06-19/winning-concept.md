# Winning Concept — 2026-06-19

**Title:** Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events (run 61, 3rd consecutive)
**Category:** code_health
**Confidence:** HIGH
**Effort:** S (~20 min, 2 files, ~10 lines)
**Autonomous-executable:** NO — nightly_review_path was true for 2 runs with no implementation.
Human required.
**Moratorium override:** YES — payment revenue bug (dunning-lock survives card fix)
**RUN 62 MANDATE:** If GH #308 still unimplemented, winner switches to GH #292/#293
(chatbot/agent_os plan-name dicts, 10 min, lower activation energy).

---

## Recommendation

Add `delete_key()` to `idempotency.py` and call it in the `stripe_webhooks.py` exception handler so Stripe can retry events that fail on first delivery.

## Why This, Why Now

`idempotency.py:check_and_record()` writes the idempotency row BEFORE the handler runs (lines 85-93). When the handler throws, `stripe_webhooks.py` raises `HTTPException(500)` — correct — but the row persists with `response_body=NULL`. On Stripe's next retry, `check_and_record` finds the existing row, returns `is_new=False`, and the handler short-circuits returning 200 without processing. The event is permanently dropped. A tenant who fixes their payment card stays dunning-locked indefinitely. Bug introduced by 47c7f8b (2026-06-16). 3 subconscious runs with no implementation (59/60/61). Active product velocity (10+ commits past 3 days) means webhook failures are increasingly likely.

## Implementation Sketch

**File 1: `backend/services/idempotency.py`** — add after `record_response()` (around line 120):

```python
async def delete_key(supabase, key: str) -> None:
    """Delete idempotency row so provider can retry on a fresh slate.

    Call inside an exception handler BEFORE re-raising.
    """
    try:
        supabase.table("idempotency_keys").delete().eq("key", key).execute()
    except Exception:
        logger.exception("idempotency delete_key failed for key=%s", key)
```

**File 2: `backend/routers/stripe_webhooks.py`** — update exception handler (~line 105):

```python
# Before:
except Exception:
    logger.exception("Stripe webhook handler failed for event %s", event_type)
    raise HTTPException(status_code=500, detail="Webhook handler failed")

# After:
except Exception:
    logger.exception("Stripe webhook handler failed for event %s", event_type)
    await delete_key(db, idempotency_key)  # allow Stripe retry
    raise HTTPException(status_code=500, detail="Webhook handler failed")
```

Add import: `from backend.services.idempotency import check_and_record, delete_key, record_response`

**Regression test** — MUST FAIL on current HEAD, PASS after fix:

```python
def test_stripe_retry_processes_after_handler_failure():
    """Idempotency row deleted on exception; Stripe retry must succeed."""
    event_id = "evt_test_idempotency_308"

    # First call: handler throws
    with patch_handler_to_raise(RuntimeError("simulated failure")):
        with pytest.raises(HTTPException) as exc_info:
            process_stripe_event(event_id, mock_checkout_payload)
        assert exc_info.value.status_code == 500

    # Row must be gone
    assert not idempotency_row_exists(f"stripe:{event_id}")

    # Second call (Stripe retry): must process normally
    with patch_handler_to_succeed() as mock_handler:
        result = process_stripe_event(event_id, mock_checkout_payload)
        mock_handler.assert_called_once()
        assert result["status"] == "ok"
```

## What This Replaces

Runs 59 and 60 carried the same winner. No previous active direction displaced.

## Confidence

**HIGH** — bug confirmed by direct inspection (delete_key absent from idempotency.py,
check_and_record confirmed insert-before-handler pattern). Fix is minimal. Pattern is safe
(delete-then-reraise is standard idempotent-recovery practice). Full sketch tested in
prior 2 runs without invalidation.

---

## Bonus A — Fix GH #292/#293 (do after main fix, ~10 min)

chatbot/agent_os absent from sms_rate_limiter._UNLIMITED_PLANS + api_key_auth._ALLOWED_PLANS +
billing_reconciliation plan caps — confirmed by grep. All new paid tenants since 2026-06-16
repricing get wrong SMS limits + cannot use Zapier. Fix: add both plan names to each set,
matching the unlimited-plan pattern from existing professional/enterprise entries.
No product debate needed — paid tiers get unlimited access same as prior top-tier plans.

## Bonus B — Add Plan-Name Guard Check 7 (AUTONOMOUS-EXECUTABLE, after Bonus A, ~15 min)

Add check 7 to scripts/check_project_invariants.py: scan sms_rate_limiter.py,
api_key_auth.py, billing_reconciliation.py for "chatbot" and "agent_os". FAIL if absent.
~15 lines Python. Must run after Bonus A so check passes on install.

## RUN 62 MANDATE

If GH #308 still unimplemented by next run:
- Winner switches to GH #292/#293 (Bonus A above, 10 min, lower activation energy)
- Reasoning: 4-consecutive-run threshold, same as GH #181 governance pivot at run 35.
  Lower activation energy (10 min vs 20 min) maximizes implementation probability.
  Both are revenue-affecting; payment severity > feature availability, but implementation
  probability also matters.
