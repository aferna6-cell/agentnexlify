# Run 91 Improvement Backlog — 2026-07-13

## Active (executing this run)

| ID | Title | Action | Status |
|----|-------|--------|--------|
| R91-W | Pre-answer referral checklist items 3/5/8 | Comment on GH #413 | Executing |
| R91-BA | Keys Koffee dedicated booking hours issue | File GH issue | Executing |

## Parking Lot (revisit next run or later)

| ID | Title | Why Parked | Revisit Condition |
|----|-------|-----------|-------------------|
| R91-P1 | Day-9+ escalation on GH #399 + #403 | 3 prior comments, diminishing returns. Day 9 not qualitatively different enough | Day 11+ or weekend threshold |
| R91-P2 | Step 9F (booking health check in nightly SKILL.md) | Supabase MCP unavailable headless; monitoring for unmonitored monitoring is low-ROI | After booking issue resolved, revisit in a future architecture pass |
| R91-P3 | Booking conversion E2E test script | Valid but HIGH effort, needs Playwright/httpx + real tenant data | After booking funnel diagnostic (#412) yields SQL results confirming flow is live |

## Questions for Human

1. **GH #413, items 9 + 10**: Item 9 (referral program user-facing copy/marketing) and item 10 (referral confirmation email to referrer on grant) — are these blockers before flipping REFERRAL_REWARD_ENABLED=1, or can they be done post-activation?
2. **Keys Koffee hours**: What are the business operating hours for Keys Koffee? (Needed to configure booking availability — 5-min fix once known.)
3. **GH #399 / #403**: Rotate AUTOPILOT_GH_TOKEN + set ANTHROPIC_API_KEY in Actions secrets. Both are Day 9 — 40 issues × 45 min queued. When?

## Frozen (do not generate ideas in these areas)

- AI-to-human handoff (frozen per governance) — unfreeze only when customer churn data shows it as #1 gap
- Widget drift topic (retired per governance)
