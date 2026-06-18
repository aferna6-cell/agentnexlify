# Debate Log — Run 2026-06-18-pm

Top 3 ideas ranked by impact: Idea 1 (payment revenue), Idea 2 (broken new tenant experience), Idea 3 (systemic prevention).

---

## Idea 1: Fix GH #308 — Webhook Idempotency Early-Write

### Challenge Round 1: Is the evidence strong enough?

**Objection:** The exception path in `stripe_webhooks.py` already raises `HTTPException(500)`, which prevents `record_response` from being called. If no response is recorded and the row has `response_body=NULL`, isn't the retry safe?

**Defend:** No. The problem is `check_and_record()` runs BEFORE the handler and inserts the row unconditionally. The row exists with `response_body=NULL`. On Stripe retry, `check_and_record` finds the row, sees `response_body=NULL`, sets `in_flight=True`, and returns `(False, cached)`. The webhook handler then returns `{"status": "ok"}` at line 71 without processing anything. The event is permanently dropped — the idempotency row blocks it forever. Confirmed by reading `idempotency.py:85-93` directly.

### Challenge Round 2: Is this the highest-leverage thing right now?

**Objection:** The platform is in active outreach mode (20+ commits on leadgen). No Stripe events are currently failing (handler is stable). The bug is latent, not active. Idea 2 (broken Zapier for all new paid tenants) is actively breaking a feature right now.

**Defend:** GH #308 has moratorium override — granted by run 59 governance. It is classified as payment revenue risk, not just latent. Any deploy that introduces a transient handler error (database timeout, external service blip) would permanently lose that payment event. With 20+ commits/day, the probability of a transient error in the next 24h is non-trivial. Dunning-lock-after-card-fix is the worst customer outcome in a SaaS billing system.

### Challenge Round 3: What could go wrong with the fix?

**Objection:** Deleting the idempotency row on exception means concurrent Stripe redeliveries both enter the handler. If Stripe sends two retries simultaneously and both see `is_new=True` (row was deleted), both process the event → double charge or double plan activation.

**Defend:** Stripe's retry logic is exponential backoff, not concurrent. After receiving a 500, Stripe waits seconds before retrying — not milliseconds. The race window is negligible in practice. Furthermore, the existing upsert with `ignore_duplicates=True` handles the concurrent-insert case anyway — if two retries race, one wins the upsert and the other gets `is_new=False`. The fix is safe. Safety note in winning-concept.md §Safety Notes covers exactly this.

### Verdict: **SURVIVES** → Winner candidate

---

## Idea 2: Fix GH #292/#293 — chatbot/agent_os Missing from Plan-Name Dicts

### Challenge Round 1: Is the evidence strong enough?

**Objection:** The grep returned results confirming old plan names in sms_rate_limiter and api_key_auth, but maybe there's fallback logic that handles unknown plans gracefully. An unknown plan might default to the most permissive behavior, not the most restrictive.

**Defend:** Direct code read: `_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}`. If a `chatbot` tenant hits the Zapier auth endpoint, their plan is not in `_ALLOWED_PLANS` → access denied. There's no fallback logic visible in the grep. `_UNLIMITED_PLANS` in sms_rate_limiter — if `chatbot` not in it, the tenant hits SMS rate limits designed for `free` tier. This is NOT permissive fallback, it's restrictive fallback. All new paid tenants are affected since repricing 3+ days ago.

### Challenge Round 2: Is this higher-leverage than Idea 1?

**Objection:** Every new paid signup on `chatbot`/`agent_os` gets broken Zapier and wrong SMS limits — that's an immediate, confirmed breakage affecting ALL new customers. GH #308 requires a handler failure to trigger. Idea 2 may be higher urgency.

**Defend:** This is a strong counter. Idea 2 breaks an immediately visible feature (Zapier integration) for all new paid tenants. However, Idea 1 has moratorium override (payment revenue) which takes governance precedence. More critically: if a `chatbot` tenant tries to pay and the webhook handler has any issue, their payment is permanently lost. The two bugs compound.

**Ruling:** Idea 2 is valid and urgent, but does not outrank Idea 1 under current governance (moratorium override means Idea 1 is mandated as winner). Idea 2 → Bonus A / Parking Lot.

### Challenge Round 3: Requires product decision on SMS limits?

**Objection:** Run 59 winning-concept.md says "product decision needed: SMS limit for chatbot tier." If we recommend without the decision, implementation is incomplete.

**Defend:** Winning-concept.md also proposes concrete defaults: chatbot = 200/day (legacy growth), agent_os = 500/day (legacy autopilot). These are defensible mappings. The recommendation includes the concrete numbers — implementer can override if product decides differently. Not a true blocker.

### Verdict: **WEAKENED** → Parking Lot (Bonus A in winner)

---

## Idea 3: Add Plan-Name Guard (check_project_invariants Check 7)

### Challenge Round 1: Is this the right time?

**Objection:** check_project_invariants already passes all 6 checks. Adding check 7 while GH #292/#293 is still broken means the check would FAIL immediately on install — it's a check for a known, already-logged bug. Timing is wrong.

**Defend:** check 7 is sequencing-dependent: it should be added AFTER GH #292/#293 is fixed, not before. The winning-concept.md sketch correctly sequences this as Bonus B (after Bonus A). It's AUTONOMOUS-EXECUTABLE. Adding it now would create a persistently failing invariant check, which would block pre-commit for all commits until fixed.

### Challenge Round 2: Is this too similar to the current active direction?

**Objection:** The subconscious system already has check_project_invariants with 6 checks. Adding check 7 is incremental maintenance, not a meaningful improvement. The improvement budget should target customer-facing or systemic issues.

**Defend:** check 7 directly prevents the class of error demonstrated by GH #292/#293 (plan-name dict drift). Without it, every future repricing silently breaks 3+ files with no automated detection. The 3-day delay between billing.py repricing and discovery of the plan-name dict gap confirms the detection gap is real.

### Challenge Round 3: What's the sequence dependency?

**Must sequence:** Fix GH #292/#293 first → then add check 7. Both could be recommended as Bonus A/B in the winner but not as independent winners. Timing is wrong for check 7 as the primary winner this run.

### Verdict: **WEAKENED** → Bonus B in winner (sequencing dependency, not primary winner)

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| GH #308 idempotency fix | **SURVIVES** → WINNER | Payment revenue, moratorium override, nightly review path |
| GH #292/#293 plan-name dicts | **WEAKENED** | Parking lot → Bonus A |
| Plan-name invariant guard | **WEAKENED** | Bonus B (sequence after Bonus A) |
| Leadgen CRM import | Not debated | Parking lot — premature, day-1 pipeline |
| Home.jsx god-class split | Not debated | Parking lot — valid but lower urgency |
