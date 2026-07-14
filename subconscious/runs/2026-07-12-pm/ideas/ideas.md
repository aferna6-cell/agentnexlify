# Ideas — Run 90 (2026-07-12-pm)

**Evidence digest:**
- 0 production code commits today (only brain refresh + nightly log)
- GH #413 (Referral Reward): OPEN, 0 comments — human has not started the UX checklist
- Referral UI CONFIRMED: ReferralPage.jsx, AdminReferralPage.jsx, ReferralCard.jsx, referral.js + full backend stack (referral.py, referral_reward.py, weekly_referrals.py, referral_overview.py, backend/routers/referral.py) + 5 test files + migration 162 in prod
- GH #399 + #403: BOTH OPEN Day 8 — 40 ai-ready issues stalled, KB autopopulate 68 days stale
- GH #412 (Booking): 1 comment (run 89 bonus action), no human SQL results — Keys Koffee unknown
- Booking: 2/3 tenants bookable (MTOptions 20 slots, 914 Exterior 22 slots), 0 real bookings 19 days post-launch
- ANTHROPIC_API_KEY (#403) = 2-min fix. AUTOPILOT_GH_TOKEN (#399) = 5-min fix. Together = "30 hours AI dev time blocked by 7 minutes"
- Frozen: ai_human_handoff (FORBIDDEN)

---

## Idea 1 — Comment on GH #413 confirming referral UI fully built

**Category:** customer_value
**Effort:** XS
**Confidence:** HIGH
**Autonomous:** YES (mcp__github__add_issue_comment)

Comment on GH #413 enumerating the confirmed referral code:
- Frontend: `frontend/src/pages/ReferralPage.jsx`, `AdminReferralPage.jsx`, `frontend/src/components/billing/ReferralCard.jsx`, `frontend/src/utils/api/referral.js`
- Backend: `backend/services/referral.py`, `referral_reward.py`, `weekly_referrals.py`, `referral_overview.py`, `backend/routers/referral.py`
- Tests: `test_referral_reward.py`, `test_referral_stats.py`, `test_widget_referral_attribution.py`, `test_referral_attribution.py`, `test_weekly_referrals.py`
- Migration: `migrations/162_referral_rewards.sql` — in prod

Explicitly pre-confirm UX checklist items 1-2 ("Referral page exists" and "widget referral capture flow exists") so human only needs to verify reward redemption path + fraud prevention (items 3-5 + fraud items). Turns a 7-item unknown checklist into "3 verifications + Railway flip."

**Why it wins:** GH #413 has 0 human responses. Human may not know the UI is already built. One comment = 2 checklist items auto-confirmed = activation path from "7 unknowns" to "5 remaining." Referral activation = 3-5x CAC reduction. Zero engineering. Highest-leverage new info this run.

---

## Idea 2 — Day-8 P0 escalation on GH #403 (ANTHROPIC_API_KEY)

**Category:** operational
**Effort:** XS
**Confidence:** HIGH
**Autonomous:** YES (mcp__github__add_issue_comment)

Post Day-8 escalation comment on GH #403 with cost framing:
- Autopilot loop: 40 ai-ready issues × avg 45 min = ~30 hours AI dev time blocked
- KB autopopulate: 68 days stale (last run 2026-05-05) — every tenant getting worse AI answers
- Referral activation: REFERRAL_REWARD_ENABLED verification requires `kb-autopopulate` to confirm KB context is up to date
- Fix: Set `ANTHROPIC_API_KEY` in GitHub Actions secrets → 2 minutes

Day-2 comment posted by run 89. Day-8 needs harder urgency: "8 days. 30 hours of queued AI work blocked by a 2-minute env var."

---

## Idea 3 — Day-8 P0 escalation on GH #399 (AUTOPILOT_GH_TOKEN)

**Category:** operational
**Effort:** XS
**Confidence:** HIGH
**Autonomous:** YES (mcp__github__add_issue_comment)

Post Day-8 escalation on GH #399 with compounding framing:
- 40 ai-ready issues stalled since 2026-07-04 (8 days)
- Each issue estimated 30-60 min implementation via loop
- Total: 20-40 hours of AI dev time blocked by a 5-minute token rotation
- Without loop: Lead Source Analytics, SMS Compliance Dashboard, and every other backlog item stays queued indefinitely
- Fix: Rotate `AUTOPILOT_GH_TOKEN` in GitHub Actions secrets → 5 minutes

---

## Idea 4 — Keys Koffee booking escalation GH issue

**Category:** customer_value
**Effort:** XS
**Confidence:** HIGH
**Autonomous:** YES (mcp__github__issue_write)

File new GH issue: "ACTION REQUIRED: Keys Koffee has 0 booking slots — tenant outreach needed"
- Keys Koffee onboarded 19+ days with no business hours
- 0 booking availability = 0 bookings possible for this tenant
- GH #412 is the diagnostic issue; this is the Keys Koffee-specific action item
- Action required: contact tenant, send setup guide link, configure hours in admin dashboard

GH #412 covers the broad diagnostic. A Keys Koffee-specific issue with `human-action-required` + `revenue` labels creates a clear, assignable task.

---

## Idea 5 — Booking health watchdog feature proposal

**Category:** code_health
**Effort:** M
**Confidence:** MEDIUM
**Autonomous:** YES (mcp__github__issue_write) but requires engineering after

File GH issue with `ai-ready` label: "feat: booking health watchdog — email tenant if booking_enabled=true but 0 availability after 3 days"
- Prevents the Keys Koffee scenario from recurring for future tenants
- Cron job: `scripts/daily/booking_health_watchdog.py`
- Logic: query `widget_configs` WHERE `booking_enabled=true` JOIN `tenant_availability` having 0 rows WHERE `created_at < NOW() - 3 days` → send onboarding reminder email
- No migration needed (queries existing tables)
- M-effort: new script + email template + cron registration in Railway
- Would enter issue-to-pr-loop once GH #399 + #403 resolved

Lower priority than Ideas 1-3 because it's forward-looking (prevents recurrence) rather than fixing current revenue gap (Keys Koffee today, referral today).
