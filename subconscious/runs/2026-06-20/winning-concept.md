# Winning Concept — Run 63 (2026-06-20)

## Title
Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events (run 63 mandate)

## Mandate Basis
Run 62 winning-concept.md §RUN 63 MANDATE: "If GH #292/#293 still unimplemented by next run → Winner switches to Bonus A (GH #308, full sketch exists, ~20 min)."

Nightly 2026-06-20 confirms: GH #292/#293 unimplemented (all 3 files still unpatched). Mandate fires. Winner switches to GH #308.

**Flagging history:** Runs 59/60/61/62/63 — 5 consecutive flagging cycles. Carried as pending_approval 4+ days.

## The Bug

`backend/services/idempotency.py` writes the idempotency row to Supabase BEFORE the webhook handler executes. If the handler throws an exception, the row persists with `response_body=NULL`. On Stripe's retry, the idempotency check finds the existing row and short-circuits — returning 200 to Stripe without running the handler. Stripe sees 200, stops retrying, event is permanently dropped.

**Impact:** Tenants who fail initial payment processing and then fix their card cannot re-enter the billing cycle. Dunning-lock persists indefinitely. No alarm fires — the silent drop only manifests as a tenant who fixed their card and still can't access the product.

**Key files:**
- `backend/services/idempotency.py` lines ~85-93 (early write before handler)
- `backend/routers/stripe_webhooks.py` (exception handler without key deletion)

## Fix Sketch

**Step 1 — Add `delete_key` to idempotency.py:**

```python
async def delete_key(supabase, key: str) -> None:
    """Delete idempotency key on handler failure so Stripe can retry."""
    await supabase.table("idempotency_keys").delete().eq("key", key).execute()
```

Place after the existing `update_key` function. No new imports required — same Supabase client pattern.

**Step 2 — Call in stripe_webhooks.py exception handler:**

In the webhook endpoint, locate the `except Exception` block that raises `HTTPException(status_code=500)`. Add the delete call BEFORE raising:

```python
except Exception as e:
    await delete_key(db, idempotency_key)
    raise HTTPException(status_code=500, detail=str(e))
```

This allows Stripe to retry on the next webhook delivery cycle. Handler failure → key deleted → retry processes event → tenant unblocked.

**Step 3 — Regression test:**

Write a test that:
1. Calls the webhook endpoint with a mocked event
2. Patches the handler to raise an exception mid-processing
3. ASSERTS on HEAD (before fix): idempotency row exists with response_body=NULL
4. ASSERTS after fix: idempotency row does NOT exist

The test must FAIL on HEAD and PASS after the fix is applied.

## Confidence
HIGH — fix sketch carried from run 59 (6+ days of review, no objections raised). Nightly 2026-06-20 confirms no code commits addressed it.

## Complexity
- Effort: S (~20 min)
- Files: 2 (`idempotency.py`, `stripe_webhooks.py`) + 1 test file
- Lines: ~15 (delete_key function + one callsite + test)
- Risk: Low — delete only runs on exception path, not success path

## Autonomous Executable
NO — payment handling code. Human approval required. Moratorium override: YES (active payment recovery bug).

## Impact
- Stops permanent payment event drops on Stripe retry
- Unblocks dunning-locked tenants who fix their card
- No change to success path (row still persists on success, as intended)

---

## Bonus A (Ready to Implement — requires human approval)

**Fix GH #292/#293 — Wire chatbot/agent_os into Plan-Name Dicts**

Day 4 unimplemented. Every new paid signup since 2026-06-16 repricing hits wrong SMS limits and Zapier 402.

Files:
- `backend/services/sms_rate_limiter.py` line 10: add `"chatbot", "agent_os"` to `_UNLIMITED_PLANS`
- `backend/services/api_key_auth.py` line 29: add `"chatbot", "agent_os"` to `_ALLOWED_PLANS`
- `backend/services/billing_reconciliation.py`: add to `_PLAN_AGENT_RUN_CAPS` (chatbot: 200, agent_os: 1500) and `_PLAN_BASELINE_AI_TOKENS` (chatbot: 1_000_000, agent_os: 2_000_000)

Note: chatbot SMS limit needs product confirmation before shipping. agent_os defaults above are safe (carry from prior run 62 sketch).

---

## Bonus B (AUTONOMOUS-EXECUTABLE — sequence-blocked until Bonus A lands)

**Add plan-name guard check_7 to check_project_invariants.py**

~15 lines Python. Greps sms_rate_limiter.py, api_key_auth.py, billing_reconciliation.py for "chatbot" and "agent_os". FAIL if absent. Prevents future plan-name drift at commit time. MUST NOT be added before Bonus A lands or every commit will fail.

---

## RUN 64 MANDATE

If GH #308 is STILL unimplemented by run 64 (confirmed via nightly log) → winner switches to GH #292/#293 (Bonus A above, full sketch exists, ~20 min).

The alternating pressure continues until one of the two revenue bugs is resolved.
