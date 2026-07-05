# Debate Log — Run 80 (2026-07-05-pm)

Top 3 ranked by impact: Idea 1 (Step 9C), Idea 2 (SMS issue-to-pr-loop), Idea 3 (Plan-name guard).

---

## Idea 1: Add Step 9C to nightly SKILL.md — Brain Connector Health Check

### Challenge Round 1 — Is the evidence strong enough?

**Challenge:** Run 79 already recommended fixing the brain connectors (GH #394 filed, pending_human). Adding Step 9C is meta-automation on top of an existing actionable issue. If the human isn't responding to GH #394, a new GH issue from Step 9C won't help either. This mirrors the moratorium meta-loop trap (runs 15-28): escalating mechanisms instead of fixing the root cause.

**Defend:** The mandate fires — this is a binding constraint from run 79, not an optional upgrade. More importantly, GH #394 addresses the *current* failure. Step 9C addresses *future* failures of the same class. Brain connector credentials will expire again (PATs have expiry dates). Step 9C is a detection mechanism, not another recommendation — once installed, it fires every night automatically. The moratorium meta-loop failed because it was recommending the same action repeatedly. Step 9C adds a fundamentally different capability: nightly automated monitoring.

### Challenge Round 2 — Is this the highest-leverage thing right now?

**Challenge:** The brain connectors have been broken for 5 days without Step 9C. The system survived. Meanwhile SMS Compliance Dashboard (12/12 council score) unlocks real customer value. Shouldn't customer value take priority over monitoring infrastructure?

**Defend:** The brain is the context layer that makes all other autonomous agents more effective. Stale brain means subconscious runs (including the SMS recommendation) are based on outdated issue state, PR state, and schema decisions. Moreover, the run 80 mandate is binding — if we skip the mandate, we undermine the governance system itself. Step 9C is the right winner; SMS Dashboard is Bonus Action.

### Challenge Round 3 — What could go wrong?

**Challenge:** Step 9C may detect false positives — if the brain refresh runs at an odd time or the log format changes, it could fire spurious GH issues and alarm fatigue sets in.

**Defend:** The detection is conservative: 3+ consecutive failure lines. A 1-day outage doesn't trigger. Format is stable (been consistent since 2026-07-01 through 5 days). SETUP includes a bypass escape hatch in comments. Alarm fatigue is a real risk but manageable — the GH issue is labeled `human-action-required` which already has attention precedent from run 79's GH #394.

**Verdict: SURVIVES → WINNER**

Evidence strong (5 consecutive days + ingestion log), mandate binding, mechanism proven (Steps 9A+9B delivered 1-cycle each), systemic improvement over point fix.

---

## Idea 2: File GH Issue for SMS Compliance Dashboard via issue-to-pr-loop

### Challenge Round 1 — Is the evidence strong enough?

**Challenge:** This idea has been circling since run 73. Full code was delivered in run 74. The human has had 5+ days and hasn't implemented. A GH issue won't reduce activation energy if the human isn't acting on it. The issue-to-pr-loop's running status is uncertain — last confirmed autonomous execution was months ago.

**Defend:** Filing a GH issue converts this from "human must open the PR themselves" to "issue-to-pr-loop can execute autonomously." Even if the loop isn't currently running, the human could trigger it manually or the issue gets picked up on the next loop restart. Code is paste-ready — the issue body would be the complete implementation, not a vague spec.

### Challenge Round 2 — Is the issue-to-pr-loop reliable enough?

**Challenge:** Nightly commit review has confirmed track record (Steps 9A, 9B, etc.). Issue-to-pr-loop has no confirmed recent execution in governance.json or nightly logs. Filing issues into an uncertain execution system is noise.

**Defend:** True — the loop status is uncertain. But filing the issue costs 2-3 min and has residual value even if loop is down (human visibility in GH). The alternative is another "pending_human" recommendation that stays stuck.

**Counter-challenge:** We already know activation energy via human hasn't worked for 5 days. If issue-to-pr-loop is uncertain, this idea has both execution paths blocked. Step 9C wins on execution reliability.

### Challenge Round 3 — Is this too similar to the active direction?

**Challenge:** Run 74 is already in `active_directions` with `status: pending_autonomous`. Filing a GH issue is just one more delivery attempt on the same item, not a new direction.

**Defend:** Fair. The governance already tracks this. Proposing it again as a winner adds to the pending queue without new mechanism.

**Verdict: WEAKENED → Parking Lot**

Genuine customer value but loop status uncertain and it's already tracked in active_directions. Step 9C mandate has higher binding force. Promote to bonus action in winning-concept.md.

---

## Idea 3: Plan-Name Guard Pre-commit Check 7

### Challenge Round 1 — Is the evidence strong enough?

**Challenge:** Parked since run 76 with "no urgency." No new plan changes in the last 3 days. test_plan_gating_new_plans.py (created with the run 62 fix) already guards against plan-gating drift. Is this proactive guard for a problem that's already covered?

**Defend:** test_plan_gating_new_plans.py tests gate *behavior* but not *code usage* of plan name strings. A developer could still hard-code `"growth"` in a new feature gate and pass the tests if they forgot to add the assertion. The pre-commit guard catches the string at commit time.

### Challenge Round 2 — Highest leverage right now?

**Challenge:** Zero production commits in 3 days. No plan changes in 3 days. There is literally no active threat this guard addresses this week. Adding it now is purely defensive prep with no urgency signal.

**Defend:** Defensive guards have most value installed before the threat, not after. The repricing happened months ago and we *still* don't have this guard.

**Counter:** Step 9C mandate is binding. Plan-name guard has no mandate, no new urgency trigger. Still parked. Same verdict as runs 76-77.

**Verdict: KILLED this run** — no new evidence of urgency. Remains parking lot. Promote to winner only when a new plan change is approaching.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Step 9C brain connector health check | **SURVIVES → WINNER** | Mandate fires, 5-day evidence, mechanism proven |
| SMS Dashboard GH issue-to-pr-loop | **WEAKENED** | Parking lot, bonus action in winning-concept |
| Plan-name guard Check 7 | **KILLED** | No urgency signal, remains parking lot |
| ops/monitoring/SETUP.md | Not debated (Idea 4) | Bonus action — should ship alongside Step 9C |
| email_sequences split | Not debated (Idea 5) | Parking lot, no new evidence |
