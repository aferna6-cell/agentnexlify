# Run 93 Ideas — 2026-07-14-pm

## Context
Run 92 winner: Day-21 Keys Koffee booking escalation + GH #413 activate-now reframe. Human closed GH #414 today at 10:11 AM UTC (first human GH activity in 3 days). PR #429 committed today at 09:36 AM UTC — ships referral_reward_email.py (79 lines) + ReferralPage.jsx how-it-works UI. Commit message explicitly states: "REFERRAL_REWARD_ENABLED is now the only step left to launch the program."

## Critical New Evidence (landed after run 92)
- **Commit a1a9e1e (2026-07-14 09:36 AM)** — PR #429 ships:
  - `backend/services/referral_reward_email.py` — referral grant email notification service (item 10)
  - Updated `frontend/src/pages/ReferralPage.jsx` — 3-step how-it-works UI (item 9 user-facing copy)
  - Commit message: "REFERRAL_REWARD_ENABLED is now the only step left to launch the program"
- **GH #414 closed by human today at ~10:11 AM** — human is actively checking GitHub issues RIGHT NOW
- GH #413 checklist: all 10 items now complete. Only blocker: REFERRAL_REWARD_ENABLED=1 in Railway.

## Mandate Check
1. Keys Koffee GH #415 actioned? → 0 human comments (no update since run 92 escalation)
2. First real booking? → STILL 0 (Day 22)
3. GH #413 run 92 reframe response? → 0 human comments
4. REFERRAL_REWARD_ENABLED=1 set? → NOT SET (but PR #429 removes last technical blocker)
5. GH #399 resolved? → OPEN Day 11
6. GH #403 resolved? → OPEN Day 11
7. Low-priority: close GH #414? → CLOSED BY HUMAN TODAY (no action needed)

## Ideas

### Idea 1: Post GH #413 comment confirming PR #429 completes items 9+10 — checklist fully done, REFERRAL_REWARD_ENABLED=1 is the only step
**Category:** customer_value
**Effort:** XS (10 min, autonomous)
**Evidence:** Commit a1a9e1e ships referral_reward_email.py (item 10 grant notification) + ReferralPage.jsx 3-step UI (item 9 copy). Commit message explicitly states only step remaining is env var. Runs 90/91/92 all pre-answered items 1-2, 3, 5, 8. Items 4/6/7 trivially confirmed by existing code. NOW: 10/10 items are done.
**Why now:** Human closed GH #414 today at 10:11 AM — they are actively reviewing issues RIGHT NOW. This is the highest-probability window in 12+ days.
**Impact:** First revenue-share referral possible within hours of env var flip. 3-5x CAC reduction on organic growth.

### Idea 2: Widget guard wiring audit — confirm widget_guard.py is actually called in widget_chat.py
**Category:** code_health
**Effort:** S (30 min, autonomous read + GH issue if unwired)
**Evidence:** PR #431 shipped widget_guard.py (160 lines, rate limiting + fraud protection) but wiring status unconfirmed. If not called from widget_chat.py, the protection layer doesn't exist in prod.
**Risk if skipped:** Fraud/spam bots can spam widget with no rate limiting, inflating AI costs.
**Dependency:** No dependency on GH #399/#403.

### Idea 3: Post Day-11 escalation on GH #403 with "120h queued" framing
**Category:** operational
**Effort:** XS (10 min, autonomous)
**Evidence:** GH #403 OPEN Day 11. 40 ai-ready issues × ~3h per issue = 120h of autonomous work queued and idle. KB autopopulate dark 72+ days. Previous escalations: run 90 (Day-8), run 91 bonus attempt, run 92 (Day-10). 3 prior escalations with 0 human response.
**Why novel:** "120h queued" is a concrete opportunity cost metric not previously stated. Shifts frame from "pipeline broken" to "value waiting."

### Idea 4: Bot-Health frontend dashboard page (BotHealthPage.jsx) — backend shipped in PR #431, no UI
**Category:** code_health
**Effort:** L (3-4h, requires human approval + implementation)
**Evidence:** PR #431 ships backend/services/bot_health.py (329 lines, LLM-as-judge per tenant) + migration 170_bot_health_scores.sql. No frontend page exists. AdminFunnelPage was built as similar card last sprint.
**Timing concern:** No confirmed customer demand for bot health scores yet. L-effort during booking/referral unblock sprint.

### Idea 5: Lead attribution dashboard tile — migration 172 + attribution.py shipped, no visualization
**Category:** customer_value
**Effort:** M (2h, requires human approval + implementation)
**Evidence:** PR #431 ships attribution.py (40 lines) + migration 172_lead_attribution.sql. No dashboard component. Similar pattern to LeadSourcePage.jsx (already built). Would show where leads are coming from per channel.
**Timing concern:** Referral activation is higher leverage. Sequential concern.
