# Winning Concept — 2026-06-21-pm (Run 65)

## Recommendation

Fix both production bugs in one PR: add `delete_key()` to idempotency.py (GH #308) and wire chatbot/agent_os into the three plan-name dicts (GH #292/#293).

## Why This, Why Now

Both GH #308 and GH #292/#293 have alternated as winner/bonus for 7 consecutive cycles (runs 59-65) with zero implementation. The alternating mandate mechanism has not produced resolution — b3279b0 (today, Jun 21) fixed 7 stale-plan-name failures across two files in one commit, proving "batch fix" in a single PR is viable and accepted in this repo. Combining both ~10-line fixes into one branch means one PR, one approval, and both moratorium-override items exit simultaneously. GH #308 is the mandate-designated winner this run (RUN 65 MANDATE fires: #292/#293 unimplemented); combining makes GH #308 primary without abandoning the SMS/Zapier fix that affects every new paid signup since Jun 16.

## Implementation Sketch

### Branch
```
fix/two-production-bugs
```

### Fix 1 — GH #308: Webhook Idempotency Early-Write (~10 lines, 2 files)

**`backend/services/idempotency.py`** — add after `record_response()`:
```python
async def delete_key(supabase, key: str) -> None:
    """Delete an idempotency key so Stripe can retry on failure."""
    try:
        supabase.table("webhook_idempotency").delete().eq("key", key).execute()
    except Exception:
        logger.warning("idempotency: failed to delete key %s — retry may be suppressed", key)
```

**`backend/routers/stripe_webhooks.py`** — in the exception handler (around the `HTTPException(500)` raise), call delete before re-raising:
```python
# Inside the except block, before raise HTTPException(status_code=500, ...):
await idempotency.delete_key(db, idempotency_key)
```
Import `idempotency` if not already imported in scope.

**Regression test** (`backend/tests/test_stripe_webhook_idempotency.py` or existing test file):
- Test must FAIL on HEAD (exception path → key persists → retry returns 200 without processing)
- Test must PASS after fix (exception path → delete_key called → retry sees is_new=True → processed)

### Fix 2 — GH #292/#293: Plan-Name Dicts (~12 lines, 3 files)

**`backend/services/sms_rate_limiter.py` line 10:**
```python
_UNLIMITED_PLANS = {"chatbot", "agent_os", "growth", "professional", "autopilot", "enterprise"}
```
*(If product decides chatbot gets a cap, add to `_PLAN_SMS_CAPS` dict instead — confirm before merge.)*

**`backend/services/api_key_auth.py` line 29:**
```python
_ALLOWED_PLANS = {"chatbot", "agent_os", "growth", "autopilot", "professional", "enterprise"}
```

**`backend/services/billing_reconciliation.py` (~lines 33-50):**
```python
_PLAN_AGENT_RUN_CAPS: dict[str, int] = {
    "chatbot": 200,      # parity-tier default — confirm with product before merge
    "agent_os": 1500,    # parity-tier default — confirm with product before merge
    "free": 25,
    "growth": 200,
    # ... existing entries unchanged
}
_PLAN_BASELINE_AI_TOKENS: dict[str, int] = {
    "chatbot": 1_000_000,      # growth-parity default
    "agent_os": 2_000_000,     # professional-parity default
    "free": 150_000,
    # ... existing entries unchanged
}
```

### Bonus B — Plan-Name Guard Check 7 (AUTONOMOUS-EXECUTABLE after combined PR merges)

After the combined PR merges, add Check 7 to `scripts/check_project_invariants.py`:
- Assert `"chatbot"` and `"agent_os"` present in `sms_rate_limiter._UNLIMITED_PLANS` (or `_PLAN_SMS_CAPS` keys)
- Assert `"chatbot"` and `"agent_os"` present in `api_key_auth._ALLOWED_PLANS`
- EXIT 1 on missing. This catches the next repricing silently omitting new plan names.

Label: `AUTONOMOUS-EXECUTABLE` — nightly review can add this the night after combined PR merges.

## What This Replaces

Alternating mandate between GH #308 (winner runs 59/61/63/65) and GH #292/#293 (winner runs 62/64). Combined PR exits the alternating loop by resolving both simultaneously.

## RUN 66 MANDATE

If the combined PR is still unimplemented by run 66: create a single GitHub issue tagged `ai-ready` with both fix sketches inlined as implementation steps — lowest-activation-energy path for autonomous loop pickup. Do not re-run the alternating mandate; escalate to a new mechanism.

## Product Confirmation Needed Before Merge

One open question on GH #292/#293: what is the correct SMS limit and agent-run cap for the `chatbot` plan ($19.99)? The sketch above uses growth-parity defaults (200 agent runs, 1M tokens, unlimited SMS). If chatbot should have a capped SMS tier, move it from `_UNLIMITED_PLANS` to `_PLAN_SMS_CAPS` with the appropriate daily limit. This is a 5-minute product decision that can be answered in PR comments.

## Confidence

HIGH — mandate honored (GH #308 primary) + active product breakage eliminated (#292/#293) + mechanism change justified by 7-cycle evidence + b3279b0 precedent for combined fix.
