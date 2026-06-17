# Winning Concept — Run 2026-06-17-pm

**Title:** Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events  
**Category:** code_health  
**Confidence:** HIGH  
**Effort:** S (~20 min, 3 files, ~15 lines)  
**Autonomous-executable:** NO — payment code requires human review (nightly review path: MEDIUM-risk with sketch)  
**Moratorium override:** YES — payment revenue bug, exempt from pending-count constraint  

---

## Problem

`idempotency.py:85-93` writes the idempotency row BEFORE the handler completes. When the handler throws an exception:

1. Row already written with `status=processing`
2. Handler failure → 500 returned to Stripe
3. Stripe retries → `idempotency.py` finds existing row → `is_new=False` → returns 200 immediately without processing
4. Event permanently dropped
5. Tenant stays dunning-locked after card fix — payment recovery never fires

Introduced by `47c7f8b` (launch hardening, 2026-06-16). GH #308 filed by nightly review 2026-06-17.

---

## Fix

Three files, one pattern: wrap handler call in try/except, delete idempotency row on exception before re-raising.

### billing.py:233-236

```python
# Before (simplified):
idempotency_service.mark_processing(event_id)
handler(event)
idempotency_service.mark_complete(event_id)

# After:
idempotency_service.mark_processing(event_id)
try:
    handler(event)
except Exception:
    idempotency_service.delete(event_id)  # allow Stripe retry
    raise
idempotency_service.mark_complete(event_id)
```

### stripe_webhooks.py:64-66

Same pattern around the event dispatch call. Confirm exact handler invocation location and wrap identically.

### idempotency.py

Add `delete(event_id: str) -> None` method if not already present. Simple DELETE by event_id. No cascades needed.

---

## Regression Test

Add to `tests/test_stripe_webhooks.py` (or `tests/test_billing.py`):

```python
def test_stripe_retry_processes_after_handler_failure():
    """Idempotency row must be deleted if handler throws, so Stripe retry works."""
    event_id = "evt_test_123"
    
    # First call: handler throws
    with patch("backend.services.billing.handler", side_effect=RuntimeError("simulated failure")):
        with pytest.raises(RuntimeError):
            process_stripe_event(event_id, mock_event_payload)
    
    # Idempotency row must be gone
    assert not idempotency_service.exists(event_id)
    
    # Second call (Stripe retry): must process normally
    with patch("backend.services.billing.handler") as mock_handler:
        process_stripe_event(event_id, mock_event_payload)
        mock_handler.assert_called_once()
```

This test must FAIL on current HEAD (proving the bug) and PASS after the fix.

---

## Safety Notes

1. **Re-raise required.** The fix must re-raise the exception after deleting the row. This returns 500 to Stripe, which triggers Stripe's retry logic.
2. **Do NOT swallow.** Any `except Exception: pass` or `except Exception: return 200` pattern here is worse than the current bug.
3. **Atomic concern.** If `idempotency_service.delete` itself throws, the original exception is lost. Consider: `finally: idempotency_service.delete(event_id)` only when exception occurred. Python idiom: save exception, delete, re-raise.
4. **Partial success.** If the handler partially updates state before throwing, re-processing on retry may be a concern. Stripe events are semantically idempotent at the business level — this is acceptable. Document in comment.

---

## Implementation Path

**Option A (nightly review):** Nightly review 2026-06-18 implements as MEDIUM-risk fix. Sketch is complete; regression test spec included. Commit + push, nightly review opens draft PR. Human approves.

**Option B (interactive):** Human invokes during next interactive session. 20 min. 3 files.

**Recommended:** Option A — nightly review has clear enough sketch to implement safely. Reduces time-to-fix from days to hours.

---

## Bonus A (after this fix lands)

Fix GH #292/#293 — wire `chatbot`/`agent_os` into 4 plan-name dicts:
- `sms_rate_limiter.py:10` — chatbot SMS limit (safe default: same as retired `growth`)
- `api_key_auth.py:29` — Zapier access for both plans
- `orchestrator.py:238/319` — branded email for agent_os
- `billing_reconciliation.py:35-49` — correct caps report for both plans

**Product decision needed:** SMS limit for chatbot tier. Propose: 200/day (matches growth legacy). Agent_os: 500/day (matches autopilot legacy).

---

## Bonus B (after Bonus A lands)

Add check 7 to `scripts/check_project_invariants.py`: scan `sms_rate_limiter.py`, `api_key_auth.py`, `billing_reconciliation.py` for current plan names (`chatbot`, `agent_os`). FAIL if any missing. **AUTONOMOUS-EXECUTABLE.** Prevents every future repricing from silently breaking these 4 files.
