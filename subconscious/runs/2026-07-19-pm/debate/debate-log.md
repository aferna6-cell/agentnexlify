# Debate Log — Run 99 (2026-07-19-pm)

## Candidates

1. Step 9F: Fix Delivery Mechanism (Direct Session Edit)
2. GH #413 Referral Activation — Booking Chain Now Complete
3. platform_flags.py Safety Registry

---

## Round 1: Idea 1 vs Idea 2

### FOR Idea 1 (Step 9F Direct)

**Urgency is real and measurable.** KB last ran 2026-07-13. It crosses the 7-day staleness threshold TOMORROW (2026-07-20). Step 9F is specifically designed to alert when KB goes stale. If it's not in SKILL.md before tomorrow's nightly, the staleness will pass silently — exactly the 72-day gap that motivated Step 9F in the first place.

**Mechanism failure is proven, not speculated.** Runs 97, 98, and 99 all confirm Step 9F absent. This is 3 consecutive data points, not variance. The root cause is structural: nightly adds bash blocks reactively; Step 9F is proactive. The nightly will never add it via its current design. Waiting for a 4th cycle is not a strategy.

**Implementation is trivially ready.** The exact bash block is written in `subconscious/runs/2026-07-17-pm/winning-concept.md`. One Edit call. Pre/post verification already specified. Risk is zero — the guard skips silently if KB_LOG is missing or unreadable.

**Mandate check 1 fires.** Governance rule: if mandate check fails, carry-forward fires unconditionally. It has fired 3 times. The carry-forward with mechanism change is the correct response.

### AGAINST Idea 1

Idea 1 has been the winner for runs 97 and 98 with no implementation. This is not because the idea is wrong — it's because the delivery mechanism is wrong. Carrying it forward a 4th time with only "do it in an interactive session" as the resolution might produce the same null result if the interactive session doesn't happen promptly.

**Counter:** The mechanism change IS the recommendation. Runs 97-98 said "nightly will implement." Run 99 says "interactive session must implement, nightly mechanism proven broken." This is a meaningful change, not repetition.

### FOR Idea 2 (GH #413 Referral)

Referral activation is pure business ROI. The system is fully built. appointment_jobs.py shipping in PR #475 completes the booking chain. The referral reward now fires on real auto-completed bookings, not just manual ones. REFERRAL_REWARD_ENABLED=1 is a single Railway secret — the lowest possible effort for the highest possible business value.

**Counter to Idea 2:** This is a human-action notification, not a system improvement. 7 comments on GH #413 already exist. The subconscious has said this before. Adding an 8th comment to a closed loop doesn't break the loop. The right action for GH #413 is PushNotification — and that's already in this run's output regardless of winner. Making it the winner would be redundant with the notification.

Additionally: the subconscious RECOMMENDS improvements to the system. GH #413 is not a system improvement — it's a human reminder. The mission brief says "identify and recommend improvements to the AgentNexLiFy platform — code quality, developer workflows, skill effectiveness, agent performance."

### Winner of Round 1: Idea 1 (Step 9F Direct)

Idea 2 is better served by PushNotification than by winning the subconscious cycle. Idea 1 addresses a proven gap in the platform's automated health monitoring.

---

## Round 2: Idea 1 vs Idea 3

### FOR Idea 1 (Step 9F Direct)

Already established: 3 cycles, KB threshold tomorrow, block ready, mechanism change is the substance.

### FOR Idea 3 (platform_flags Safety Registry)

**Nightly flagged a real risk.** The nightly commit review (2026-07-19) explicitly noted: "if a DB row is accidentally set to 0 for something like `voice_chat_max_tokens`, the Twilio/Claude call would receive `max_tokens=0` and fail." This is a real failure mode. It's not hypothetical — the code exists today and the bypass is by design.

**The risk grows over time.** platform_settings is a new table (migration 175, PR #476). As more features adopt DB-flag control, the probability of an operator setting a dangerous key grows. A safety registry today costs little; a silent production outage from `max_tokens=0` costs much more.

**Not blocked by GH #399.** Idea 3 does not require issue-to-pr-loop or human approval to implement. The subconscious can recommend a direct file write.

### AGAINST Idea 3

**No current production risk.** The nightly explicitly noted: "No current production rows at risk — prod seeded values are all '1' (enable flags)." The risk is theoretical today.

**Premature abstraction.** platform_settings has 1 migration, 1 PR, 2 days of production history. A safety registry for 2 keys (voice_enabled, referral_enabled) is over-engineering. Wait until 3+ keys exist with diverse types before creating a classification system.

**Timing.** Step 9F is urgent because KB crosses the threshold TOMORROW. Idea 3 has no date-bound urgency signal.

**Carry-forward is forced.** Governance rule: mandate check 1 has failed 3 times. Carry-forward fires unconditionally when the mandate check fails. Idea 3 cannot override a mandatory carry-forward.

### Winner of Round 2: Idea 1 (Step 9F Direct)

Idea 3 is a good future improvement but has no date-bound urgency and low current risk. Step 9F has explicit urgency (KB threshold tomorrow) and a failed mandate check that fires carry-forward unconditionally.

---

## Final Synthesis

**Winner: Step 9F — Fix Delivery Mechanism (Recommend Direct Session Implementation)**

**Mechanism change vs run 97/98:** The winning recommendation is NOT "carry forward again with the same delivery channel." The substantive change is:
- Runs 97, 98: delivery mechanism = nightly (autonomous)
- Run 99: delivery mechanism = next interactive session, explicit human approval

The reason for the mechanism change: 3 consecutive nightly cycles confirm the nightly cannot proactively add Step 9F. Root cause is structural (reactive vs proactive). The SKILL.md-edit channel works for reactive blocks; Step 9F requires the proactive channel.

**Urgency escalation:** KB crosses 7-day threshold 2026-07-20 (tomorrow). Run 99 is the last opportunity to add Step 9F before the first staleness event it was designed to catch.

**GH #413 escalation:** Will surface in PushNotification with specific context (booking chain now complete with PR #475). Not the winning concept, but surfaced.

**Parking lot confirmations:**
- appointment_completion.py → SHIPPED (PR #475, appointment_jobs.py). Remove from parking lot.
- BotHealthPage.jsx → SHIPPED (PR #475). Remove from parking lot.
- AttributionPage → SHIPPED (PR #475). Remove from parking lot.
- conversation_enrichment_job.py scheduling → continue parking. Needs Supabase MCP + GH #399.
- kb_hybrid enable → continue parking. Needs settings UI or GH #399.

**Confidence: HIGH**
- Mandate check failure is unconditional carry-forward trigger
- KB urgency is date-bound and measurable
- Mechanism root cause is fully understood
- Implementation is trivially ready (block written in run 97)
