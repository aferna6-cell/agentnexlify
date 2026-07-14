# Run 93 Improvement Backlog — 2026-07-14-pm

## Parking Lot (not winner this run, keep for future runs)

### P1 — GH #403 Day-11+ escalation (WEAKENED, 3rd recycle)
- **Why parked:** 3 prior escalations (runs 90, 91, 92) with 0 human response. Diminishing returns pattern.
- **Novel angle when revived:** "120h queued" framing (40 issues × ~3h = concrete opportunity cost metric)
- **When to promote:** If GH #413 gets response but #403 still open in run 94 — pair it with referral activation progress to show what the pipeline would unlock
- **Effort:** XS
- **Category:** operational

### P2 — Widget Guard Wiring Audit
- **Why parked:** Bonus A status — lower priority than referral activation, but still important
- **Action needed:** grep backend/routers/widget_chat.py for `from backend.services.widget_guard` or `widget_guard.check_request`
- **If unwired:** file GH issue with labels `bug`, `ai-ready`, `security`, title: "wire(widget): widget_guard.py rate limiter not called in widget_chat.py endpoint"
- **Effort:** S (30 min autonomous)
- **Category:** code_health

### P3 — Bot-Health Frontend Dashboard (BotHealthPage.jsx)
- **Why parked:** L effort, no confirmed customer demand, backend-only feature (PR #431 bot_health.py)
- **When to promote:** After referral activation + first booking — next product sprint
- **Data available:** backend/services/bot_health.py (329 lines), migration 170_bot_health_scores.sql
- **Pattern:** Same as AdminFunnelPage.jsx (similar card/chart component pattern)
- **Effort:** L
- **Category:** customer_value

### P4 — Lead Attribution Dashboard Tile
- **Why parked:** M effort, referral activation higher priority
- **Data available:** attribution.py (40 lines), migration 172_lead_attribution.sql
- **Pattern:** Similar to LeadSourcePage.jsx (already built, existing chart pattern)
- **When to promote:** After referral activation live, as next dashboard enhancement
- **Effort:** M
- **Category:** customer_value

### P5 — Keys Koffee Business Hours Direct Outreach Reminder
- **Status:** GH #415 has run 92 Day-21 escalation comment (ID: 4963248261). Day 22 as of today.
- **Observation:** Human closed #414 today but hasn't commented on #415. Still needs direct contact with Keys Koffee owner.
- **When to promote to winner:** If GH #413 referral activates but booking still 0 at Day 25 — separate escalation cycle needed

### P6 — KB Autopopulate Status Check (GH #403 secondary)
- **Why parked:** Blocked by GH #403 (ANTHROPIC_API_KEY). 72+ days dark = 72+ days of KB drift.
- **Impact:** knowledge-base/wiki/ stale for all AI agents using KB context
- **Resolution:** Human sets ANTHROPIC_API_KEY in Railway (2-minute fix per run 90 escalation)

## Key Observations This Run

1. **The subconscious loop works.** Runs 90→91→92→93 progressively answered all 10 GH #413 checklist items without any human research. The loop eliminated all blockers autonomously.

2. **PR #429 was the keystone commit.** Human wrote referral_reward_email.py and updated ReferralPage.jsx TODAY. The commit message "REFERRAL_REWARD_ENABLED is now the only step left" means the human already KNOWS — they just need a push.

3. **GH #414 closure is a live signal.** Human closed #414 (duplicate issue) at 10:11 AM today. This is the first GitHub activity since run 90's initial comment. They are present and reviewing.

4. **Day 22 with 0 real bookings is critical.** Both booking (Keys Koffee) and referral activation are stalled by human inaction, not code. The subconscious has done its job. The bottleneck is now human decision speed.
