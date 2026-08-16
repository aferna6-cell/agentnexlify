# Debate Log — Run 107 (2026-08-16-pm)

Top 3 by impact: Idea 1 (security/code_health), Idea 3 (customer_value), Idea 4 (code_health).

---

## Idea 1: Fix scoring_config.py missing block_demo_role

### Challenge
- Evidence strong? GH #661 filed this morning — confirmed by nightly. Naming is precise (`block_demo_role`, not a generic security concern). PASS.
- Highest leverage right now? Two confirmed instances (appointment_briefs + scoring_config) is a pattern. route-security-guard-audit SKILL.md exists precisely for this. Audit has not been run yet. We may be fixing one instance while 3 others remain. Counter-argument: we can't audit all 20+ routers in a single subconscious run; fixing the confirmed instance closes the known hole.
- What could go wrong? Same logic applies as appointment_briefs.py run 106. Router-level `dependencies=[Depends(block_demo_role)]` is a single line change + import. Blast radius is zero for non-demo tenants. Demo tenants lose write access to scoring config — this is correct behavior.
- Similar to rejected idea? No. Appointment_briefs.py was EXECUTED in run 106. This is a different router with identical class of gap. No prior rejection.
- Too similar to current active_direction? Active direction is "route-security-guard-audit SKILL.md" — this IS that direction applied to the next confirmed instance. Not duplication; it's progress.

### Defend
- GH #661 is direct confirmation — nightly filed it same day it was found
- SKILL.md written this cycle makes implementation trivial (6-step guide)
- Appointment_briefs.py fix (run 106) provides proven pattern to copy
- AUTONOMOUS-EXECUTABLE: low risk, known pattern, confirmed bug
- Counter to "fix one while others remain": SKILL.md exists for the broader audit; fixing the known-confirmed instance now and scheduling the broader audit is the right sequencing

### Verdict: SURVIVES — primary candidate

---

## Idea 3: Step 9I nightly paying-tenant zero-conversation alert

### Challenge
- Evidence strong? Parking lot since run 104 — two cycles without new evidence. The idea is sound in principle but no new data surfaced showing paying tenants are actually churning. "Churn prevention is revenue-critical" is a statement, not evidence.
- Highest leverage right now? No confirmed paying tenant at risk. The gap is real but no urgency signal. AUTOPILOT_GH_TOKEN expired = kb autopopulate blocked = nightly itself is degraded. Fixing degraded infrastructure beats adding new steps to degraded infrastructure.
- What could go wrong? Supabase query in nightly requires the KB autopopulate blocker (GH #403) resolved first — otherwise Step 9I would fire but lack context. Adding nightly steps when the nightly itself can't reach the API is premature.
- Similar to rejected idea? Not frozen. Was parking lot, not rejected. Difference is timing.
- Too similar to current active direction? No, but timing is wrong given GH #403 blocks the infrastructure it would run on.

### Defend
- Churn prevention has real business value — losing a paying tenant is $20-100/month recurring
- Query is simple: `SELECT tenant_id FROM subscriptions WHERE plan IN ('chatbot','agent_os') AND last_conversation_at < now() - interval '14 days'`
- Step 9I can be written as a conditional block that skips if SUPABASE_ACCESS_TOKEN unavailable
- Two-cycle parking lot suggests this idea keeps surfacing for a reason

### Verdict: WEAKENED — good idea, wrong timing. GH #403 blocks infrastructure it needs. Parking lot for run 108.

---

## Idea 4: ai_usage_guard in appointment_briefs.py service layer

### Challenge
- Evidence strong? Run 106 deferred it explicitly. Comment in code acknowledges the gap. Evidence is the deferred TODO.
- Highest leverage right now? appointment_briefs.py already has block_demo_role from run 106. The ai_usage_guard is a second layer. How often do appointment briefs actually hit AI token limits? No evidence of tenant hitting the cap. Fixing it is correct but not urgent.
- What could go wrong? `reserve_ai_tokens()` signature requires full tenant dict. Run 106 said the dict wasn't available at router level. Need to check if it's available in service layer. Could require refactoring the service call chain — not XS.
- Similar to rejected idea? Not rejected. Deferred from run 106 with explicit note.
- Too similar to current active direction? Current direction is route-security-guard-audit (Idea 1). This is a parallel concern in the same file.

### Defend
- The deferred TODO is a debt marker. Guard coverage should be consistent across routers.
- `_get_current_tenant()` returns the tenant dict — `reserve_ai_tokens(tenant, tokens)` can consume it directly
- The guard prevents real resource exhaustion per tenant at scale
- Atomic, small, consistent with existing pattern

### Counter-challenge: If tenant dict IS available, why did run 106 defer? Possible the function signature changed, or the function was looking for a specific dict shape. Risk of subtle bug if dict keys differ. This requires reading the actual `reserve_ai_tokens()` signature before committing — not a blind port.

### Verdict: WEAKENED — correct to fix, but requires reading reserve_ai_tokens() signature first. Risk of subtle integration bug if dict keys differ from what the guard expects. Better as a separate implementation task after manual review. Parking lot.

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| 1. scoring_config.py block_demo_role | SURVIVES | Confirmed bug, SKILL.md guides it, proven pattern |
| 3. Step 9I zero-conversation alert | WEAKENED | Wrong timing, blocked by GH #403 infrastructure |
| 4. ai_usage_guard appointment_briefs | WEAKENED | Requires dict key verification, risk of subtle bug |

Winner: Idea 1.
