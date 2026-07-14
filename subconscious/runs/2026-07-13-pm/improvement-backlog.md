# Run 92 Improvement Backlog — 2026-07-13-pm

## Active (pending human action)

### P0 — Keys Koffee First Booking (GH #415)
**Status:** Run 92 Day-21 escalation comment posted
**Action required:** Human emails Keys Koffee today, gets business hours, configures in dashboard
**Expected outcome:** First real booking within hours of configuration
**Revenue signal:** Funnel 0/3 → 1/3 booked
**Re-measure:** 2026-07-23 (per GH #412 comment 3 suggestion)

### P0 — Referral Reward Activation (GH #413)
**Status:** 4 autonomous comments (runs 89-92), 0 human responses
**Remaining items:** Item 9 (copy — 30 seconds), Item 10 (email — skip for MVP)
**Action required:** Decide on Item 9 copy, set REFERRAL_REWARD_ENABLED=1 in Railway
**Revenue signal:** 3 tenants can share referral links immediately

### P0 — Autopilot Loop (GH #399)
**Status:** OPEN Day 10, 40 ai-ready issues stalled
**Action required:** Rotate AUTOPILOT_GH_TOKEN (5 min, full instructions in issue)
**Compounding:** Each day of delay = 4 loop cycles that don't run

### P0 — KB Autopopulate (GH #403)
**Status:** OPEN Day 10, KB stalled 70+ days
**Action required:** Set ANTHROPIC_API_KEY in GitHub Actions secrets (2 min, instructions in issue)

---

## Parking Lot (deferred)

### Close GH #414 as duplicate of GH #415
- Low priority, maintenance action
- Both issues cover Keys Koffee business hours
- #415 is more detailed; #414 can be closed

### Lead Source Analytics PR
- GH issue filed (ai-ready label), run 85 winner
- Blocked by GH #399 (autopilot loop stalled)
- Unblocks when #399 resolved

### Referral Grant Email Notification (Item 10)
- Not a blocker for activation
- 30-min follow-up sprint: Resend transactional email on referral conversion
- Schedule after REFERRAL_REWARD_ENABLED=1 is set and first referral confirmed

---

## Killed This Run

| Idea | Reason |
|---|---|
| Idea 3: Close GH #414 | Low leverage, deferred to run 93 low-priority |
| Idea 4: GH #413 item 10 code-verify | Already answered in run 91 comment |
| Idea 5: GH #412 cross-issue sprint summary | Thread saturated with good analysis today |
