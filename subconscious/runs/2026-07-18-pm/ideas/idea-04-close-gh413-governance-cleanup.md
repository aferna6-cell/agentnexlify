# Idea 04 — Close GH #413 + Governance Cleanup for PRs #475/#476

**Category:** Operational / Governance  
**Effort:** XS (GH API calls + governance.json updates)  
**Confidence:** HIGH  
**ROI:** 1.4

## The Idea

Multiple governance items need cleanup after today's PRs:

1. GH #413 (REFERRAL_REWARD_ENABLED=1): PR #476 seeded `referral_reward_enabled=1` in
   `platform_settings`. `referral_reward.reward_enabled()` reads from `flag_enabled()` which
   checks DB first. Referral program IS live. GH #413 should be commented + closed.

2. appointment_jobs.py (GH #454): Implemented in PR #475 as
   `backend/services/automation/scheduled/appointment_jobs.py`. GH #454 closed per PR.

3. BotHealthPage.jsx (GH #465): Implemented in PR #475. GH #465 closed.

4. AttributionPage (GH #453): Implemented in PR #475. GH #453 closed.

5. KB hybrid + rerank: NOW LIVE (not pending settings UI / GH #399).

## Evidence

- PR #476 (6b0b0bc, 2026-07-18 12:26 UTC): migration 175, platform_settings rows seeded.
- `referral_reward.py:42`: `return flag_enabled("referral_reward_enabled", env_default=env_on)`
- PR #475 (23b1da5, 2026-07-18 12:12 UTC): appointment_jobs.py, BotHealthPage, AttributionPage.
  Closes: GH #454, #465, #453.

## Why It's WEAKENED as winner

- This is housekeeping, not a system improvement.
- The PR merges already close the GH issues automatically.
- Governance cleanup happens in Phase 6 (Persist) of every run — not a winner.
- Better framing: all of these are Phase 6 corrections in THIS run, plus a Bonus Action
  (comment on GH #413 explaining platform_settings activation path).

## Verdict

WEAKENED → Bonus Action. Handle in Phase 6 governance corrections + Bonus A comment on GH #413.
