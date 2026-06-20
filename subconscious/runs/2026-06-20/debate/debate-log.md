# Debate Log — Run 63 (2026-06-20)

## Setup

**Mandate status:** RUN 63 MANDATE fires. Run 62 winning-concept.md §RUN 63 MANDATE: "If GH #292/#293 still unimplemented by next run → Winner switches to Bonus A (GH #308, full sketch exists, ~20 min)." Nightly 2026-06-20 confirms GH #292/#293 unimplemented — mandate fires.

**Candidates entering debate:**
- Idea 1: Fix GH #308 — Webhook Idempotency (RUN 63 MANDATE)
- Idea 2: Fix GH #292/#293 — chatbot/agent_os Plan-Name Dicts (carry-over run 62)
- Idea 3: Add plan-name guard check_7 (AUTONOMOUS-EXECUTABLE, sequence-blocked)

Idea 4 (GH #263 migrations) and Idea 5 (kb-autopopulate.sh) eliminated before debate — insufficient urgency against active revenue bugs.

---

## Round 1: Idea 1 vs Idea 2

**Idea 1 argument (Fix GH #308):**
> Mandate fires. Five consecutive flagging cycles (runs 59/60/61/62/63). Payment event drops are silent and permanent — tenants who fix their card after dunning CANNOT re-enter billing cycle. The bug hides behind Stripe's 200 response on retry: idempotency row persists with response_body=NULL, Stripe sees 200, stops retrying, event is gone. No alarm fires. No tenant ticket helps. The only signal is a dunning-locked tenant who fixed their card and still can't access the product. Revenue impact compounds daily. Fix is surgical: `delete_key()` + one callsite in exception handler. ~20 min. Full sketch exists from run 59.

**Idea 2 argument (Fix GH #292/#293):**
> Idea 2 carries run 62's mandate basis — it WAS the winner last cycle. Every new paid signup since 2026-06-16 repricing hits this: wrong SMS limits (50/day free-tier cap instead of unlimited), Zapier 402. Four days of new tenants impacted. Idea 2 is ALSO ~20 min. Why does GH #308 win over GH #292/#293 given symmetric urgency?

**Ruling on Idea 2 challenge:**
Mandate mechanism is explicit and non-negotiable. Run 62 winner was GH #292/#293 specifically to relieve alternating mandate pressure. GH #292/#293 was NOT implemented in the 24h window. Mandate fires: pivot to GH #308 per written governance contract. This is the same logic that produced run 62's winner (GH #308 was unimplemented 4 consecutive cycles → mandate fired → pivoted to GH #292/#293 → GH #292/#293 unimplemented → mandate fires → pivot back). Both bugs carry moratorium_override=true. GH #308 wins on mandate precedence, not higher intrinsic urgency.

**Idea 2 status: WEAKENED** — remains valid as Bonus A. Not disqualified on merit; disqualified on mandate hierarchy.

---

## Round 2: Idea 1 vs Idea 3

**Idea 3 argument (plan-name guard check_7):**
> check_project_invariants.py passes all 6 checks and has autonomous precedent — checks 10/11/12/13 all landed autonomously. Check_7 is ~15 lines of grep logic. It would have caught GH #292/#293 at commit time. Why not execute it now autonomously instead of waiting?

**Idea 1 rebuttal:**
> Sequence dependency is fatal. If check_7 is added BEFORE GH #292/#293 is fixed, the three files it checks (sms_rate_limiter.py, api_key_auth.py, billing_reconciliation.py) are still missing chatbot/agent_os. Check_7 FAILS immediately. Every subsequent commit fails pre-commit. This locks the repo until either check_7 is reverted or GH #292/#293 is fixed. Adding a guard before fixing what it guards is backwards. Check_7 is AUTONOMOUS-EXECUTABLE and will land as Bonus B after GH #292/#293 fixes.

**Idea 3 status: KILLED as winner candidate** — survives as Bonus B, sequence-blocked.

---

## Round 3: Final validation of Idea 1

**Challenge: Is the fix sketch correct?**

From run 59 winning-concept.md + nightly 2026-06-20 confirmation:

```python
# backend/services/idempotency.py — CURRENT (lines 85-93 approximate)
async def check_and_create_idempotency_key(supabase, key, ttl_seconds):
    existing = await supabase.table("idempotency_keys").select("*")...
    if existing.data:
        return existing.data[0]  # early return if key exists
    await supabase.table("idempotency_keys").insert({
        "key": key,
        "created_at": ...,
        "response_body": None  # row written BEFORE handler runs
    }).execute()
    return None
```

```python
# backend/routers/stripe_webhooks.py — CURRENT (exception handler)
try:
    result = await handle_event(event)
    await update_idempotency_key(db, idempotency_key, result)
except Exception as e:
    # Row already persists with response_body=NULL
    # Stripe retry hits → finds key → returns 200 → drops event
    raise HTTPException(status_code=500, detail=str(e))
```

**Fix:**
```python
# Add to idempotency.py:
async def delete_key(supabase, key: str) -> None:
    await supabase.table("idempotency_keys").delete().eq("key", key).execute()

# Modify stripe_webhooks.py exception handler:
except Exception as e:
    await delete_key(db, idempotency_key)  # allow Stripe retry
    raise HTTPException(status_code=500, detail=str(e))
```

**Regression test contract:**
- FAIL on HEAD: raise exception in handler after row write → query idempotency_keys for key → row exists
- PASS after fix: same exception → key deleted → Stripe retry would reprocess

**Challenge: Any risk of double-processing?**
Stripe retry is the correct behavior. The handler FAILED — the event was not processed. Deleting the key allows Stripe to retry, which is the desired outcome. The only risk is if the handler is non-idempotent and the retry processes twice after a partial success. The answer: FastAPI handlers should be idempotent for Stripe webhooks — this is Stripe's architectural requirement regardless of our implementation. The alternative (keeping the dead idempotency row) guarantees zero processing, which is worse than the theoretical double-processing risk.

**Idea 1 status: SURVIVES → WINNER**

---

## Final Verdict

| Idea | Status | Path |
|------|--------|------|
| 1: Fix GH #308 | **WINNER** | Mandate fires. Execute on human approval. |
| 2: Fix GH #292/#293 | Bonus A | Human approval required. Sequence: after or in parallel with Winner. |
| 3: Add check_7 | Bonus B | AUTONOMOUS-EXECUTABLE after Bonus A lands. |
| 4: GH #263 migrations | Parked | ROI 2.3 — triage before fix. |
| 5: Fix kb-autopopulate | Parked | ROI 1.8 — address after revenue bugs clear. |

**Winner: Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events (run 63 mandate)**
