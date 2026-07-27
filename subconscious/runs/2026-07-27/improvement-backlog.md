# Run 105 Improvement Backlog — 2026-07-27

## Active (winner)

**PR #577 merge-readiness comment** (run 105 winner)
- Category: operational
- Mechanism: GH comment on PR #577
- Autonomous: YES
- Status: executed this run

---

## Bonus actions (executed this run)

**GH #500 Day-7 heartbeat comment** — dated manual ping while Step 9H awaits merge. Day 7 of Actions outage. References run 101 checklist. Signals PR #577 readiness.

---

## Parking lot

| Idea | Condition to promote |
|------|---------------------|
| Managed Agents Phase 0 kickoff GH issue | Human approves run 103 winner (pending_approval gate); or run 106 finds run 103 winner-concept.md contains issue body |
| email_sequences regression test audit | GH #399 resolved (autopilot-issue-loop can file ai-ready issue) |
| PR #575 merge reviewer comment | PR #575 still open in run 106 |
| Step 9I: VOYAGE_API_KEY rotation schedule | Promote when VOYAGE_API_KEY next rotation date known |
| Lead Source Analytics dashboard (run 85) | GH #399 resolved; issue-to-pr-loop active |
| Booking first-conversion audit | Supabase queryable in session context |

---

## Permanent retirement (do not re-propose)

- **Widget drift topic** — retired at run 70, human-only task
- **ai_human_handoff** — frozen (governance.json frozen_ideas list)

---

## Open issues needing human action (standing flags)

| Issue | Blocker | Age |
|-------|---------|-----|
| GH #500 | Actions spending limit | 7 days |
| GH #399 | AUTOPILOT_GH_TOKEN rotation | 22+ days |
| GH #403 | ANTHROPIC_API_KEY in Actions secrets | 22+ days |
| GH #413 | REFERRAL_REWARD_ENABLED=1 not set | 14+ days |
| GH #415 | Keys Koffee business hours | 14+ days |
| PR #577 | Review + merge (Steps 9G+9H) | 3 days |
| PR #575 | Review + merge (tenant-silence alert) | 4 days |

---

## Questions for run 106

1. Did the PR #577 merge-readiness comment accelerate human review?
2. Did Step 9H fire on nightly-2026-07-28?
3. GH #500 resolved? Which credential fix first (billing vs token vs API key)?
4. Managed Agents Phase 0: approved or still pending?
5. KB freshness: still within 7-day threshold?
