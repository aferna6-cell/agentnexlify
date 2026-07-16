# Idea Generation — Run 95 (2026-07-16)

## Evidence Digest

**26 commits in 24h — heavy day.** Two CRITICAL root-cause fixes emerged:

1. `6cc3419` (fix #439): The AI widget prompt **never included the booking URL**. MTOptions had 21 leads / 0 bookings. 914 Exterior had 8 leads / 0 bookings. Now fixed via `booking_prompt.py`. First real bookings are now technically possible.

2. `f143de5` (fix #441): Appointment reminders and automations **silently never fired** because `send_appointment_reminders` filtered on `'booked'` (a status that never exists — appointments are always `'confirmed'`). This was likely dead since booking shipped. Now fixed.

Other notable: RLS lockdown (#436 — genuine PUBLIC anon vulnerability removed), FK index migration (#437), Agent OS auto-send fixed (#447/#450), booking notification lifecycle complete (#440–#444). Run 94 winner (widget_guard LRU) implemented by `d73072a`. GH #454 filed by nightly: post-appointment automations still can't fire because appointments stay `confirmed` forever — no auto-complete job.

**Persistent blockers:** GH #399 Day 13+ (AUTOPILOT_GH_TOKEN expired, 30 ai-ready issues stalled), GH #413 REFERRAL_REWARD_ENABLED=1 still not set, GH #403 still open (KB 72+ days dark).

---

### Idea 1: Implement appointment auto-complete cron job (GH #454)

**Evidence:** GH #454 filed today by nightly review. `f143de5` just fixed the status filter bug (automations were dead). `6cc3419` just injected the booking URL (first bookings now possible). The automation chain is now: Book → `confirmed` → [missing: auto-complete job] → `completed` → review request / rebook / aftercare fire. Without the auto-complete transition, every booking that comes in sits `confirmed` forever and the entire post-booking automation funnel produces zero output.

**Action:** Implement `appointment_completion.py` — a cron-callable function that queries appointments where `end_time < now()` AND `status = 'confirmed'` AND `completed_at IS NULL`, marks them `completed`, and triggers the `appointment_completed` rule engine event. Wire into `appointment_reminders.py` scheduler or add as GH Actions workflow.

**Impact:** Unlocks review requests, rebook prompts, and aftercare automations for every tenant with bookings. Timing is optimal: bookings are now possible for the first time (URL fix landed today). Without this, first bookings produce zero follow-up, wasting the retention loop.

**Category:** customer_value

---

### Idea 2: GH #399 Day-13 escalation comment — frame as opportunity-cost blocker

**Evidence:** nightly-2026-07-16 deferred GH #399 as "noted for context" without filing an escalation comment. 30 ai-ready issues have been blocked since 2026-07-04 (13 days). Issues include Lead Source Analytics (run 85 winner), SMS Compliance Dashboard, and 28 others. Single AUTOPILOT_GH_TOKEN rotation unlocks all of them.

**Action:** Post Day-13 escalation comment on GH #399 with opportunity framing: "30 ai-ready issues blocked — rotating AUTOPILOT_GH_TOKEN today unlocks Lead Source Analytics, SMS Compliance Dashboard, and 28 others. Single Railway secret update, 2 minutes." Autonomous via `mcp__github__add_issue_comment`.

**Impact:** If human sees the opportunity-cost framing, single 2-min action unblocks 30 queued issues.

**Category:** operational

---

### Idea 3: Step 9F — Add KB autopopulate staleness check to nightly SKILL.md

**Evidence:** KB last populated 2026-05-05 (72+ days). GH #403 is the proximate block. Steps 9B/9C/9D/9E were all implemented and provide operational visibility. No step currently monitors KB staleness in every nightly run. From run 94 parking lot.

**Action:** Add Step 9F block to `.claude/skills/nightly-commit-review/SKILL.md`: read `knowledge-base/log.md` last entry date, compute days since last run, if >7 days escalate with comment on GH #403 (or create new issue if #403 resolved). Autonomous-executable via nightly SKILL.md addition pattern.

**Impact:** Systematic KB staleness detection on every nightly run. Prevents 72-day blind spots.

**Category:** operational

---

### Idea 4: Referral reward final-push escalation (GH #413 — Day 24)

**Evidence:** REFERRAL_REWARD_ENABLED=1 still not set after 5 autonomous comments across runs 89–93. 0 human responses to any comment. Referral checklist 10/10 complete (PR #429 a1a9e1e). Only step left: env var in Railway.

**Action:** Post final comment on GH #413 with a numbered "5-step visual walkthrough" of exactly what the human sees when activating: (1) open Railway dashboard, (2) click agentnexlify-backend, (3) Variables tab, (4) add REFERRAL_REWARD_ENABLED=1, (5) redeploy. Ultra-specific reduces friction. OR recommend human push notification via this session.

**Impact:** If activated, first referral-converted lead possible within hours. 3–5x CAC reduction on referrals. Mechanism novelty: specificity > authority.

**Category:** customer_value

---

### Idea 5: BotHealthPage.jsx — frontend dashboard for bot health service

**Evidence:** PR #431 shipped `bot_health.py` service. No frontend page exists for tenants to see bot health. From run 93/94 parking lot. `feature-build` skill applies.

**Action:** Create `frontend/src/pages/BotHealthPage.jsx` — read `/api/bot-health/{client_id}`, display health score, last test date, failure reasons. Wire into Sidebar.jsx + App.jsx routing. L effort (~2 days).

**Impact:** Tenants can see if their bot is healthy. Reduces support requests about "why is my bot not working."

**Category:** customer_value
