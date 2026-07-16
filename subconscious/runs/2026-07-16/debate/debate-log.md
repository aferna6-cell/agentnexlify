# Debate Log — Run 95 (2026-07-16)

Top 3 ideas debated: Idea 1 (Appointment auto-complete), Idea 2 (GH #399 escalation), Idea 3 (Step 9F KB staleness).

---

## Idea 1: Appointment auto-complete cron job (GH #454)

### Round 1 Challenge
Is this premature? The booking URL fix (#439) was merged TODAY. No real bookings have happened yet. Why implement post-appointment automations before a single appointment completes? Shouldn't we wait to see if bookings actually start flowing before adding more automation surface?

### Round 1 Defend
Waiting is wrong here. The implementation is additive and has zero risk. The time to wire the post-booking funnel is before the first booking — not after. If the first 10 bookings come in over the next week and no review requests fire, the tenants lose 10 review opportunities permanently. The fix is a cron job querying `appointments` where `end_time < now() AND status = 'confirmed'` — no migration, no schema change, no risk. GH #454 already has the implementation proposal. The nightly review flagged it as MEDIUM with a full implementation sketch. Timing is optimal precisely because the booking URL fix just landed.

### Round 2 Challenge
GH #454 is labeled MEDIUM risk by the nightly. Is the autopilot-issue-loop the right execution path? It's been dead 13 days (#399 unresolved). If the loop is dead, recommending this as "autonomous-executable via nightly code-change channel" is misleading.

### Round 2 Defend
This can be executed via the nightly code-change channel (not the autopilot-issue-loop). The nightly-commit-review already implements LOW-risk code changes autonomously (e.g., d73072a, 061582c, e848b87). An `appointment_completion.py` service that moves past-confirmed appointments to `completed` status is 15–20 lines, no new dependencies, no schema changes — clearly LOW-risk additive. The nightly can implement it directly without the autopilot-issue-loop. The implementation sketch in GH #454 removes all ambiguity.

### Round 3 Challenge
What if the auto-complete job races with in-progress appointments? A booking scheduled for 10am–11am that the staff extends to 11:30am will be auto-completed at 11:00am while still in progress.

### Round 3 Defend
The implementation sketch guards this: only complete appointments where `end_time + 30min grace < now()`. A 30-minute buffer prevents premature completion of running appointments while still catching completed ones within 24h. This is the same pattern used by appointment_reminders.py (buffer-based scheduling). The race condition is real but solvable with a single guard condition.

**Verdict: SURVIVES → WINNER**
Evidence: direct (GH #454 filed today). Implementation: LOW-risk additive. Timing: optimal (booking URL just fixed). Execution path: nightly code-change channel. All three rounds defended.

---

## Idea 2: GH #399 Day-13 escalation comment

### Round 1 Challenge
5 prior escalation comments across multiple runs (Steps 9D/9E from nightly reviews, governance notes). 13 days of inaction. The human either hasn't seen GH #399 or doesn't prioritize rotating credentials. One more comment doesn't change the mechanism.

### Round 1 Defend
This comment has a different framing: opportunity-cost rather than system-health. Prior comments said "loop stalled, please rotate token." This comment says "30 ai-ready issues blocked — 2-minute action unlocks Lead Source Analytics, SMS Compliance Dashboard, and 28 others." The ROI framing is new. Prior escalations focused on the failure; this one focuses on the upside.

### Round 2 Challenge
If the human hasn't responded to 13 days of escalation, does a 14th comment change anything? The mechanism may be exhausted. Same problem as GH #413 referral (5 autonomous comments, 0 responses).

### Round 2 Defend
Point accepted. The mechanism has diminishing returns. However, the nightly today flagged GH #399 but did NOT post an escalation comment — there's an actual monitoring gap. Filling it costs nothing and preserves the escalation chain. But as a standalone WINNER, this is weak.

### Round 3 Challenge
The fundamental issue is credential rotation, which requires access to Railway dashboard and GitHub PAT settings — information only the human has. No amount of comments changes that.

**Verdict: WEAKENED → Parking Lot / Bonus Action**
The comment is worth posting as a bonus action but not strong enough to be the primary winner. Mechanism partly exhausted. Idea 2 demoted.

---

## Idea 3: Step 9F — KB autopopulate staleness check in nightly SKILL.md

### Round 1 Challenge
The KB is stale because GH #403 blocks it. Step 9F would detect and escalate what is ALREADY KNOWN and already tracked in governance.json. Is this adding real monitoring value or creating escalation noise for a known-blocked situation?

### Round 1 Defend
Step 9F is not about GH #403 specifically — it's about systematic KB staleness detection on every nightly run, regardless of the root cause. If GH #403 is eventually resolved and a new blocker emerges, Step 9F catches it. Steps 9B/9C/9D/9E all passed this same challenge: they monitor things that "should be" caught elsewhere but weren't. KB was 72 days dark before it was caught at all.

### Round 2 Challenge
Steps 9B/9C/9D/9E all provided genuinely new monitoring coverage for things not tracked anywhere. GH #403 staleness IS tracked: governance.json has `kb_autopopulate_stale_days`, and every recent nightly log mentions it. Step 9F adds a SKILL.md block that does what the nightly already does manually. That's documentation of existing behavior, not new monitoring.

### Round 2 Defend
The nightly currently notes KB staleness ad-hoc but doesn't escalate with GH issue creation or structured escalation logic. Step 9F would make the escalation automatic and conditional (e.g., if KB stale >7 days AND no open KB issue exists → create one). The value is in the automation of escalation, not just the detection.

### Round 3 Challenge
GH #403 is already open. Creating a new GH issue when #403 is already open creates duplicate noise. Step 9F would need deduplication logic, which adds complexity to a 3-line SKILL.md addition.

**Verdict: WEAKENED → Parking Lot**
Step 9F has systematic value but weaker than Idea 1 at this moment. The KB staleness is already tracked. Priority should go to the appointment auto-complete which unlocks a new automation revenue path. Promote Step 9F to run 96 if GH #403 is resolved and KB resumes.

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Appointment auto-complete cron job (GH #454) | SURVIVES → **WINNER** | Implement via nightly code-change channel |
| GH #399 Day-13 escalation | WEAKENED | Bonus action — post comment on GH #399 |
| Step 9F KB staleness | WEAKENED | Parking lot — run 96 candidate |
| Referral final push (GH #413) | Not debated — mechanism exhausted | Push notification to human instead |
| BotHealthPage.jsx | Not debated — L effort, low urgency | Backlog |
