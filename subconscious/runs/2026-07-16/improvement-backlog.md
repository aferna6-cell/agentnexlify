# Improvement Backlog — 2026-07-16 (Run 95)

## Active

- **Implement appointment auto-complete cron job** — `appointment_completion.py`, 15-min scheduler, marks past-confirmed appointments completed + fires `appointment_completed` rule event. Unlocks review requests, rebook prompts, aftercare. GH #454. Autonomous-executable via nightly code-change channel.

## Parking Lot (survived debate, not chosen)

- **Step 9F: KB autopopulate staleness check in nightly SKILL.md** — add Step 9F block to detect KB last-run date, escalate if >7 days. WEAKENED: GH #403 already tracked, duplicate escalation risk. Run 96 candidate if GH #403 resolved.
- **BotHealthPage.jsx** — frontend dashboard for bot_health service (PR #431). L effort. Customer value: tenants see bot health. Deferred until post-booking automation chain is complete.
- **Post-split-test-repair SKILL.md** — still useful for god-class split follow-ups. Runs 36/39 long-term carry.

## Rejected This Run

- **GH #399 Day-13 escalation as standalone winner** — WEAKENED. Mechanism partly exhausted (13 days, no response). Demoted to bonus action. Real fix requires human action (Railway credential rotation).
- **GH #413 referral final push** — mechanism exhausted (5 autonomous comments, 0 responses). Human action only. Push notification path recommended.

## Standing Human-Required Actions (no autonomous path)

| Issue | Status | Days | Action Needed |
|-------|--------|------|---------------|
| GH #413 | REFERRAL_REWARD_ENABLED=1 not set | Day 24 | Set env var in Railway → deploy |
| GH #415 | Keys Koffee business hours | Day 24 | Email/call owner for hours |
| GH #399 | AUTOPILOT_GH_TOKEN expired | Day 13 | Rotate PAT in Railway → redeploy |
| GH #403 | KB autopopulate stalled | Day 13 | Resolve access token / Actions secret |

**Note:** `6cc3419` (booking URL fix) landed today. First bookings are now technically possible. Activating REFERRAL_REWARD_ENABLED before first bookings ensures those customers become potential referrers from day 1.

## Questions for Next Run

1. Did appointment auto-complete ship? Did first real booking trigger a review request?
2. GH #399: Has human rotated AUTOPILOT_GH_TOKEN? If yes — 30 issues now queue up, lead source analytics PR will open.
3. Did booking URL fix (#439) generate any real bookings in the 24h after merge?
