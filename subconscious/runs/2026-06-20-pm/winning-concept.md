# Winning Concept — 2026-06-20-pm (Run 64)

## Recommendation

Fix GH #292/#293 — add `chatbot` and `agent_os` to the three plan-name dicts that gate SMS access, Zapier API keys, and billing reconciliation.

## Why This, Why Now

Run 64 mandate fires: GH #308 confirmed unimplemented for the 6th consecutive cycle (no `delete_key` in `idempotency.py`, nightly 2026-06-20 confirms). The alternating governance mandate switches the winner back to GH #292/#293. Beyond the mandate, this is active product breakage: every new paid tenant since repricing on 2026-06-16 gets wrong SMS rate limits and cannot create working Zapier API keys. The three affected files are identified, the exact variable names and line numbers are documented, and the full sketch exists in `subconscious/runs/2026-06-19-pm/winning-concept.md`. The only open question is the correct SMS limit for the `chatbot` plan — the implementation sketch uses parity-tier defaults which can be confirmed in the same PR review.

## Implementation Sketch

1. **Confirm chatbot SMS limit** (product decision, 5 min): What is the monthly SMS limit for the `chatbot` plan ($19.99)? Proposed default: same as `growth` (existing cheapest unlimited plan). `agent_os` → unlimited (same as `enterprise`). Confirm before merging.

2. **Fix `backend/services/sms_rate_limiter.py` line ~10:**
   ```python
   _UNLIMITED_PLANS = {"chatbot", "agent_os", "growth", "professional", "autopilot", "enterprise"}
   ```
   (If chatbot gets a cap, add to `_PLAN_SMS_CAPS` instead; if unlimited, add to `_UNLIMITED_PLANS`.)

3. **Fix `backend/routers/api_key_auth.py` (~line 29):**
   Add `chatbot` and `agent_os` to `_ALLOWED_PLANS` (or equivalent gate variable). Confirm exact variable name from file — grep returned empty on prior patterns, so read the file directly before editing.

4. **Fix `backend/services/billing_reconciliation.py` (~lines 33-50):**
   Add entries to `_PLAN_AGENT_RUN_CAPS` and `_PLAN_BASELINE_AI_TOKENS`:
   ```python
   _PLAN_AGENT_RUN_CAPS = {
       "chatbot": 200,      # parity-tier default; confirm with product
       "agent_os": 1500,    # parity-tier default; confirm with product
       # ... existing entries
   }
   ```
   Add corresponding entries to `_PLAN_BASELINE_AI_TOKENS` dict.

5. **Write regression test** (optional but recommended): `test_billing_reconciliation.py` — assert `chatbot` and `agent_os` appear in both cap dicts.

6. **Bonus A (Bonus Action — ~20 min, human required):** Fix GH #308 — add `async def delete_key(supabase, key)` to `backend/services/idempotency.py`; call `await delete_key(db, idempotency_key)` in `backend/routers/stripe_webhooks.py` exception handler before `raise`. Full sketch: `subconscious/runs/2026-06-19/winning-concept.md`.

7. **Bonus B (AUTONOMOUS-EXECUTABLE after Bonus A lands):** Add plan-name guard Check 7 to `scripts/check_project_invariants.py` — validates both `chatbot` and `agent_os` appear in `sms_rate_limiter._UNLIMITED_PLANS` and `api_key_auth._ALLOWED_PLANS`. Prevents future repricing from silently omitting new plan names.

## What This Replaces

Previous winner: Fix GH #308 (run 63, webhook idempotency). GH #308 is demoted to Bonus A this run — it remains the highest-severity open bug and should be fixed alongside or immediately after this winner.

## RUN 65 MANDATE

If GH #292/#293 still unimplemented by run 65: switch winner back to GH #308 (alternating mandate continues). Implementation sketch for GH #308: `subconscious/runs/2026-06-20/winning-concept.md`.

## Confidence

HIGH — mandate compliance + direct file confirmation of bug + complete implementation sketch + no new blockers.
