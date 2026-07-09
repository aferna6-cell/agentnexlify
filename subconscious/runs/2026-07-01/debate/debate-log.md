# Debate Log — Run 75 (2026-07-01)

Top 3 ranked by impact. Each idea challenged with hard objections, defended with evidence.

---

## Idea 1: De-scoped SMS Compliance Backend (Mandate Item)

### Round 1: Is the mandate still binding?

**Challenge:** Nightly 2026-07-01 independently filed a GH issue for the full SMS Dashboard (both backend + JSX). Issue-to-pr-loop will now attempt autonomous implementation of the complete feature. The run 74 mandate was designed to unblock a stuck human task — but the autonomous path may already handle it. Is the de-scope mandate now moot?

**Defend:** The mandate says "if SMS not shipped: de-scope to backend endpoint only." SMS is confirmed not shipped at time of this run (both files MISSING, confirmed by nightly commit review). The mandate fires. The GH issue is a welcome parallel path, not a mandate override. If issue-to-pr-loop ships the full feature, both paths converge. If it ships only backend (due to JSX complexity), the mandate recommendation is prescient. Mandate is not moot.

### Round 2: Does recommending de-scope conflict with the filed GH issue?

**Challenge:** The nightly GH issue specifies full scope (backend + JSX page + sidebar). The subconscious recommending "backend only" now creates conflicting guidance. The human sees: GH issue says full scope, subconscious says backend only. Which wins?

**Defend:** Subconscious recommendations are advisory. The human decides. But the conflict signal is valid — the subconscious de-scope directive predates the GH issue. Now that issue-to-pr-loop covers the full scope autonomously, the de-scope mandate loses practical urgency. The subconscious should update active_directions to "pending_autonomous" and move on.

### Round 3: Is this the highest-leverage recommendation this run?

**Challenge:** SMS is now in the autonomous pipeline (GH issue filed). The subconscious adding another "ship SMS" recommendation is additive noise. No new information. The same recommendation made 4 times (runs 73, 74, mandate fires = run 75, de-scoped version). The system is stuck on SMS — propose something different.

**Defend:** Partially valid. The SMS path is covered. The de-scope recommendation is a mandate formality, not high-leverage original analysis. Switching winner is appropriate when autonomous coverage exists.

**Verdict: WEAKENED** — mandate honored (de-scope noted), but GH issue autonomous path makes this the lowest-activation-energy it's ever been. Update active_directions to pending_autonomous. Winner switches to Idea 2.

---

## Idea 2: Zapier plan_status Enforcement (GH #107)

### Round 1: Does the moratorium block this?

**Challenge:** Moratorium active at true_pending ~4. Governance `max_pending_approvals: 2` already violated. Adding a new item to the queue makes the moratorium worse, not better. Parking lot condition for this idea was "true_pending ≤ 1" — we're at ~4.

**Defend:** Moratorium override precedent exists for security/revenue bugs. GH #308 (payment loss from idempotency bug) and GH #292+293 (plan-name gate failure for all new paid tenants) both received moratorium_override: true. Zapier #107 is the same class: cancelled tenants continue receiving platform value without payment. Revenue leakage + access control violation. Not a feature request — a security debt.

More importantly: this is AUTONOMOUS-EXECUTABLE (same nightly class as Check 11/12, test creation, SKILL.md additions). Zero items added to human queue. Moratorium measures HUMAN pending items. Autonomous items execute without human approval — they do not count against moratorium threshold.

### Round 2: Is the evidence strong enough after 62 days of inaction?

**Challenge:** GH #107 has been open 62 days. Zero production fix attempts. If this were truly high-priority, it would have been implemented already. Maybe the fix is harder than bug-patterns.md suggests?

**Defend:** bug-patterns.md notes "Skeleton — confirm exact path before remediation" — meaning the fix location needed verification. That's a verification gap, not a scope gap. The fix itself is well-understood: `plan_status IN ('active','trialing')` check in `_get_api_key_client`. The reason it wasn't implemented is that subconscious kept re-recommending SMS Dashboard, and moratorium kept blocking new items. This is the first run where SMS has autonomous coverage, freeing bandwidth.

### Round 3: Is this truly a high-leverage action compared to customer-facing features?

**Challenge:** Zapier enforcement prevents cancelled tenants from getting free access. But how many cancelled tenants are actively using Zapier? Zapier usage requires the agent_os plan ($99.99/mo). If they cancel, their API keys should stop working. How material is this?

**Defend:** Every cancelled tenant with an active Zapier integration continues receiving platform value after subscription ends. This is revenue leakage on every cancelled agent_os subscriber. More importantly: it's an access control violation — the system claims to enforce plan gates but silently bypasses them for API key consumers. This undermines the integrity of the entire billing enforcement model. Fix is 2 files, ~30 min, zero human queue impact.

**Verdict: SURVIVES** — moratorium override justified (security/revenue, AUTONOMOUS-EXECUTABLE), 62-day debt, first clean window to recommend it.

---

## Idea 3: AI-to-Human Handoff v1

### Round 1: Is there new evidence justifying re-recommendation?

**Challenge:** 7 consecutive failed recommendations (runs 4, 21, 29, 38 × 3 reps). 76 days pending. Same infrastructure argument made in runs 38 and 41. The bottleneck is clearly execution commitment (M-effort, human required), not information or readiness. What's different this run?

**Defend:** No new evidence. customer-gaps.md says "Critical for complex queries" across all industries — still true. os_outbound_mirror.py ships the infrastructure — still true. But these facts have been true since run 38 (2026-05-28). No new activation energy reduction. No new framing.

### Round 2: Does continued non-implementation signal it should be de-prioritized?

**Challenge:** 7 failed recs + 76 days = the system's track record says this won't happen. Proposing it an 8th time without a new activation-energy reduction is noise. The subconscious brief says "each run builds on previous learning" — learning from 7 failures should be: stop proposing this until something changes.

**Defend:** Customer gap is genuine and growing. GoHighLevel advantage widens every day. But the brief also says "rejected ideas teach the system what NOT to propose" — 7 recs without implementation should trigger a different approach, not identical re-recommendation.

### Round 3: Should this be frozen?

**Challenge:** Governance freeze_threshold is 3 rejections. This has effectively been rejected/unimplemented 7 times. Should it be frozen?

**Defend:** It's been unimplemented but not explicitly rejected. The human hasn't said "don't do this." It's a capacity problem, not a direction problem. But until SMS Dashboard ships and moratorium reduces, proposing M-effort human-required items is wasted signal.

**Verdict: KILLED this run** — no new evidence, 7-run delivery failure chain, moratorium active. Re-evaluate when: SMS Dashboard ships, true_pending ≤ 2, and a new activation-energy reduction emerges (e.g., someone builds the trigger detection first as an S-effort isolated piece).

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| 1. De-scoped SMS Backend | WEAKENED → parking lot | GH issue covers autonomous path; update to pending_autonomous |
| 2. Zapier plan_status enforcement | **SURVIVES → WINNER** | Security/revenue override, AUTONOMOUS-EXECUTABLE, 62-day debt, clean window |
| 3. AI-to-Human Handoff v1 | KILLED | 7-run failure chain, no new evidence, moratorium active |
| 4. Plan-Name Guard Check 7 | Not debated (lower rank) | Parking lot — human required, lower urgency than Zapier |
| 5. Home.jsx god-class split | Not debated (lower rank) | Parking lot — M-effort, wait for SMS + Zapier to ship |
