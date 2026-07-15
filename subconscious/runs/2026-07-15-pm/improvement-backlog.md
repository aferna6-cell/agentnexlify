# Improvement Backlog — 2026-07-15-pm (Run 95)

## Active

- Add regression test in `backend/tests/test_widget_chat.py` asserting booking URL is injected in AI prompt when `booking_enabled=True` (and absent when `False`). Autonomous-executable via nightly code-change channel. 30 minutes, no new deps.

## Parking Lot (survived debate but not chosen)

- **Step 9F: nightly infra staleness escalation** — add to `.claude/skills/nightly-commit-review/SKILL.md`: query `human-action-required` issues open >7 days, post Day 7/14/21 milestone comments, add `critical` label at Day 14. WEAKENED: marginal value at Day 13+ for existing issues. Promote once GH #399/#403 resolve (demonstrates the gap is real).
- **Attribution Dashboard GH issue** — file issue for `AttributionPage.jsx` with `ai-ready` label. WEAKENED (bonus action): loop blocked by GH #403, but filing queues it for activation. PR #431 ships attribution.py + migration 172. Promote once GH #403 resolved.
- **BotHealthPage.jsx GH issue** — file for the new bot_health.py service (largest from PR #431). Not debated. Promote when loop unblocked.
- **KB refresh script** (`scripts/kb-refresh-local.sh`) — unstick 72-day stale KB by running kb-autopopulate.sh with local Claude CLI. Not debated. Promote as operational quick win.

## Rejected This Run

None killed outright — Ideas 2 and 3 weakened to parking lot rather than rejected.

## Persistent Blockers (human action required)

- **REFERRAL_REWARD_ENABLED=1** in Railway Variables — Day 24+, 4 autonomous comments with no response. Checklist 10/10 complete. 2-minute action.
- **Keys Koffee business hours** — email/call tenant. Day 24+. Fix: dashboard → Settings → Booking Hours. 3 leads unable to book.
- **GH #399** — rotate AUTOPILOT_GH_TOKEN. Day 13+. Unblocks 40 ai-ready issues.
- **GH #403** — add ANTHROPIC_API_KEY to GitHub Actions secrets. Day 13+. Unblocks KB autopopulate + autopilot loop.

## Questions for Next Run

1. Did nightly commit the booking URL regression test? (check nightly-2026-07-16 log)
2. Did any of the 3 critical booking-area fixes (#439 booking URL, #441 reminders dead, #442 reschedule) result in a first real booking?
3. Should Step 9F be promoted now that GH #399/#403 demonstrate the 14-day escalation pattern concretely?
4. Is BotHealthPage.jsx ready to spec, or does bot_health.py router need more endpoints first?
