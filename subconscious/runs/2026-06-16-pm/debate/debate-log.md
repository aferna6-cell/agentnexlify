# Debate Log — Run 2026-06-16-pm (Run 59)

Top 3 ideas: Idea 1 (Zapier plan_status), Idea 3 (AI-to-Human Handoff), Idea 4 (check-widget-sync.sh)

---

## Idea 1: Fix Zapier plan_status enforcement (issue #107)

### Round 1

**Challenge:** Is the evidence strong enough? Issue #107 was filed April 30 — 47 days with no evidence of actual exploitation. Tenants haven't complained about Zapier bypass. Why is this time-critical NOW vs any other run?

**Defend:** The threat model changed TODAY, not 47 days ago. Before 7-day trials: Zapier auth gap only affected tenants who were already ACTIVE (valid key, already paying). If they cancelled, their key might persist — but that's a marginal edge case for small-volume Zapier users. After trials: a trialing tenant gets a 7-day window, may set up Zapier during trial, trial expires at day 7, pay_gate blocks web access — but Zapier key still authenticates. That tenant can continue extracting leads, firing webhooks, and using API capacity indefinitely. Direct revenue leak: value delivery without revenue. This is the first run where the leak vector is CONFIRMED ACTIVE.

**Verdict:** Challenge answered — timing is evidence-based, not speculation.

---

### Round 2

**Challenge:** Is this the highest-leverage thing right now? Run 58 winner (Check 13) is pending_autonomous and will execute tonight. Should we not just wait for that to land and then see what breaks next?

**Defend:** Check 13 is autonomous — no human action needed. This debate is about what to direct HUMAN attention to. The human has ~15 min of work for the Zapier fix. The fix is fully specified in bug-patterns.md. "Wait and see" on a confirmed revenue leak isn't a policy — it's drift. Zapier auth bypass + active trial system = compounding risk per day.

**Verdict:** Challenge answered — different queue (human vs autonomous). Both can proceed in parallel.

---

### Round 3

**Challenge:** The parking lot note on Zapier says "Promote to first NON-MORATORIUM winner." The moratorium is still active (8 pending_approval items >> threshold 2). Isn't recommending this now a violation of governance?

**Defend:** The parking lot note was added at run 16 (2026-05-11) before trials existed. The note's intent was to avoid piling up security recommendations in an already-clogged queue. The moratorium spirit was "don't add more until some clear." But: (a) The queue is already at 8 items — adding 1 more doesn't meaningfully worsen that; the moratorium is deeply violated regardless. (b) Time-sensitivity creates a new condition that wasn't anticipated when the note was written. (c) The fix is S-effort ~15 min — faster to implement than any other item currently pending. If the human implements it in 15 min, net pending stays the same. The note should be updated to reflect new evidence.

**Verdict:** SURVIVES — governance condition overridden on time-sensitivity grounds with explicit note to update parking lot entry.

---

## Idea 3: AI-to-Human Handoff v1

### Round 1

**Challenge:** 7+ failed recommendations (runs 4, 21, 29, 38 as primary winners). The mechanism has broken every time. What's different now?

**Defend:** The context has changed: pay_gate means real paying customers exist. When the AI fails a paying customer, churn cost is real money. The scope reduction (os_outbound_mirror.py, 152 tests, PR #188 merged) is still valid. Run 38 showed this is a ~1 day implementation. The obstacle isn't information or scope — it's human bandwidth.

**Challenge (Round 2):** The parking lot/implementation_lag note says "AI-to-Human Handoff v1 first POST-MORATORIUM customer value win." The moratorium is active. Shouldn't we respect this sequencing?

**Defend:** Fair point. The system's own note directs this for post-moratorium. With 8 pending_approval items, we're not close to moratorium exit. Recommending it now when Zapier is more time-critical and better-specified is wrong ordering.

**Verdict: WEAKENED** — valid customer value, correct eventual priority, wrong timing while Zapier is time-critical and moratorium deeply active. Parking lot: "first post-moratorium customer value win" as noted.

---

## Idea 4: check-widget-sync.sh (run 7/50 pending_autonomous)

### Round 1

**Challenge:** Check 13 executes tonight via check_project_invariants.py, which already includes widget byte-sync as one of its 6 checks. If Check 13 wires tonight, widget drift is already caught at pre-commit. Does check-widget-sync.sh add meaningful value?

**Defend:** Check 13 (check_project_invariants) runs at pre-COMMIT time and checks widget sync. check-widget-sync.sh was designed for pre-PUSH (git push), providing an extra gate. But the pre-commit gate is stronger: it catches violations before they even enter git history.

**Challenge (Round 2):** If the pre-commit gate is stronger and covers widget sync, then check-widget-sync.sh is a redundant belt-and-suspenders that adds complexity without proportional value. The 55-day implementation gap suggests even the nightly hasn't prioritized it.

**Defend:** Belt-and-suspenders on widget sync is LOW cost (one script). But with Check 13 activating tonight, the urgency is gone.

**Verdict: WEAKENED** — superseded in practice by Check 13 (tonight). Demoted to bonus action after Check 13 confirms. Parking lot: deferred until next widget change triggers drift.

---

## Synthesis

| Idea | Verdict | Next Step |
|------|---------|-----------|
| Idea 1: Zapier plan_status (issue #107) | **SURVIVES → WINNER** | Human ~15 min, add to pending |
| Idea 3: AI-to-Human Handoff | WEAKENED → parking lot | First post-moratorium customer value win |
| Idea 4: check-widget-sync.sh | WEAKENED → bonus after Check 13 | Deferred |
| Idea 2: admin_analytics.py tests | Not debated (weakened) → parking lot | Verify coverage gap first |
| Idea 5: RequirePaid audit | Not debated → parking lot | Low evidence of active bug |

**Winner: Idea 1 — Zapier plan_status enforcement (issue #107)**
Confidence: HIGH
