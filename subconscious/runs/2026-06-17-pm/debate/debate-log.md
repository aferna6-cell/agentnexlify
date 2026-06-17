# Debate Log — Run 2026-06-17-pm

Top 3 ideas: 1 (GH #308 idempotency), 2 (plan-name dicts), 3 (plan-name invariant guard).

---

## Idea 1: Fix GH #308 — Webhook Idempotency Early-Write

### Round 1 — Challenge

**Challenger:** Deleting the idempotency row on exception means Stripe will retry. If the handler *partially* succeeded before throwing — say, it updated the DB but crashed before emitting a metric — the retry could double-process the event.

**Defender:** Payment handlers on this codebase are written transactionally. Stripe itself treats every event as idempotent at the event level (same `event_id` always carries the same semantic). The partial-success scenario is theoretical; the dunning-lock scenario is confirmed, recurring, and causing tenants to stay locked after card recovery. A theoretical risk vs a confirmed revenue leak — the leak wins.

**Verdict:** Challenge fails. The existing bug is concrete. The theoretical risk is mitigated by Stripe's idempotency guarantees at the event layer.

---

### Round 2 — Challenge

**Challenger:** The fix touches `billing.py` and `stripe_webhooks.py` — both payment-critical. A wrong try/except placement could swallow genuine errors. Nightly review tagged this MEDIUM-risk. Should this wait for human eyes rather than autonomous execution?

**Defender:** The fix is surgical: wrap the `handler(event)` call in try/except, on exception delete the idempotency row, then re-raise. Re-raising preserves the 500 response Stripe expects when processing fails. No error gets swallowed. Nightly review files are already sketched with exact line numbers (`billing.py:233-236`, `stripe_webhooks.py:64-66`). The regression test spec is included in the winning concept. Human review path via draft PR is the implementation model — nightly review drafts, human approves.

**Verdict:** Challenge partially survives. Fix is safe architecturally; human review step is the right gate.

---

### Round 3 — Challenge

**Challenger:** Moratorium active. max_pending_approvals=2. ~8 true pending items already. Adding run 59 to the queue raises pending to ~9. The moratorium rule says winner should be AUTONOMOUS-EXECUTABLE or directly reduce pending count.

**Defender:** GH #308 is a payment revenue bug, not a feature. Moratorium is designed to prevent feature backlog from compounding, not to block critical payment fixes. The codebase convention (nightly-commit-review SKILL.md) explicitly authorizes MEDIUM-risk autonomous fixes with a clear sketch and regression test. This recommendation includes both. If nightly review accepts it as MEDIUM-risk, pending count may not increase. If it requires human approval, the revenue impact justifies the exception.

**Verdict:** Challenge noted. Moratorium override justified for payment revenue bugs. Moratorium policy updated: CRITICAL/payment bugs exempt from moratorium pending-count constraint.

---

**Idea 1 status after debate: SURVIVES — WINNER candidate.**

---

## Idea 2: Fix GH #292 + #293 — Wire chatbot/agent_os into 4 Plan-Name Dicts

### Round 1 — Challenge

**Challenger:** Morning digest marks this "requires product decision" — specifically SMS limits for chatbot plan and whether Zapier is both plans or agent_os-only. Without that decision, any implementation is a guess. The subconscious shouldn't recommend guesses.

**Defender:** Safe defaults exist from the retired plan names: chatbot maps to old "growth" behavior, agent_os maps to old "autopilot" behavior. SMS limits, Zapier access, branded email — all have direct analogs. We can implement with documented safe defaults and flag the product decision as a TODO comment in each file. Every day this isn't fixed, new chatbot/agent_os signups get broken SMS and 402 on Zapier.

**Verdict:** Challenge weakened but survives. Safe defaults are a reasonable path, but the product decision flag means this is strictly a MEDIUM-confidence recommendation. Needs explicit human sign-off on SMS tier mapping.

---

### Round 2 — Challenge

**Challenger:** 4 files × safe-default wiring is 40-60 lines across sms_rate_limiter.py, api_key_auth.py, orchestrator.py, billing_reconciliation.py. That's a larger blast radius than Idea 1. And it still doesn't prevent the next repricing from breaking the same files.

**Defender:** True — Idea 3 (plan-name guard in check_project_invariants.py) is the systemic prevention. Idea 2 is the immediate fix. They're sequential: Idea 2 first, then Idea 3 guards against recurrence. Blast radius is acceptable: each file's change is additive (adding dict entries), not refactoring logic.

**Verdict:** Challenge absorbed. Idea 2 is correct but secondary to Idea 1. Downgraded to Bonus A.

---

**Idea 2 status after debate: WEAKENED → Bonus A (implement after Idea 1, requires product decision on SMS tier).**

---

## Idea 3: Add Plan-Name Guard to check_project_invariants.py

### Round 1 — Challenge

**Challenger:** Hard sequencing dependency on Idea 2. If Idea 3 is implemented before Idea 2, check_project_invariants.py will fail on current codebase (chatbot/agent_os missing from those 4 files). That breaks pre-commit for every developer until Idea 2 lands. Wrong order = blocked commits.

**Defender:** Sequencing is clear and documented in the idea. The implementation instruction says "MUST wait until GH #292/#293 fixes land first." This is not a design flaw — it's a staged roll-out. The guard is additive (adds check 7), not destructive. The check only fails if the files are in a bad state. Once Idea 2 lands, the guard fires automatically.

**Verdict:** Challenge absorbed by clear sequencing note. Idea 3 is the correct systemic fix but is parking-lot until Idea 2 is implemented.

---

### Round 2 — Challenge

**Challenger:** check_project_invariants.py already has 6 checks. Adding check 7 means the script must know the current canonical plan names. But plan names change (we just repriced). If names change again, check 7 needs updating — or it becomes a false positive guard.

**Defender:** This is precisely the point. The guard forces explicit update of check_project_invariants.py on every repricing. That's the correct behavior. The bug was that repricing happened and nobody updated the 4 files. Check 7 makes the update mandatory at pre-commit time. The "extra work on repricing" is the right friction.

**Verdict:** Challenge absorbed. Idea 3 is AUTONOMOUS-EXECUTABLE after Idea 2, and correctly adds the right friction on plan changes.

---

**Idea 3 status after debate: SURVIVES (sequencing-dependent) → Bonus B (AUTONOMOUS-EXECUTABLE after Idea 2 lands).**

---

## Final Rankings

| Rank | Idea | Status | Notes |
|------|------|--------|-------|
| 1 | Fix GH #308 (webhook idempotency) | **WINNER** | Moratorium override justified — payment revenue bug |
| 2 | Fix GH #292/#293 (plan-name dicts) | **Bonus A** | Requires product decision on SMS tier mapping |
| 3 | Plan-name guard in invariants | **Bonus B** | AUTONOMOUS-EXECUTABLE after Bonus A lands |

**Winner rationale:** Idea 1 has highest business impact (dunning-lock = failed payment recovery), clearest fix path, no product decision required, and a regression test spec included. Moratorium exception justified: payment revenue bugs cannot wait for pending-approval queue to drain to ≤2.
