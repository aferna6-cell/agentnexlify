# Improvement Backlog — Run 89 (2026-07-11-pm)

## Active

- **File "Referral Reward Activation Pre-Gate" GH issue** — REFERRAL_REWARD_ENABLED=1 after Migration 162 in prod. Human-action-required: verify UX checklist then flip Railway var. Zero engineering. Labels: revenue, human-action-required. AUTONOMOUS-EXECUTABLE via GitHub MCP. (run 89 winner)

## Bonus Actions (execute this run)

- **Comment on GH #412** — post PR #404 findings: MTOptions confirmed 20 live slots, 914 Exterior confirmed 22 slots post-prod-bug-fix (impossible hours corrected to 17:00). Keys Koffee still needs real hours from tenant. Narrows investigation scope.
- **Comment on GH #403** — Day-2 escalation: 40 ai-ready issues stalled, kb-autopopulate 67 days since last run (2026-05-05), Lead Source Analytics GH #409 queued.

## Parking Lot (survived debate but not chosen)

- **Diagnose Supabase MCP availability in headless sessions** — nightly and subconscious sessions both lack Supabase MCP despite org-level install. Fix enables Steps 9F+ and future autonomous DB diagnostics. Blocked by SUPABASE_ACCESS_TOKEN unknown state (#394). (run 90 candidate)
- **Add Step 9F to nightly SKILL.md — tenant availability hours check** — Keys Koffee-specific hypothesis. Add after human confirms Keys Koffee needs hours seeded. Schema: widget_configs + tenant_availability or booking_hours JSON column. (run 90 candidate, conditional on Keys Koffee hours gap confirmed)
- **Keys Koffee business hours onboarding** — 914 Exterior and MTOptions both bookable. Keys Koffee is the one remaining unresolved tenant. Needs real business hours from tenant or manual seed. Human-action. (run 90 candidate)
- **Referral Reward Pre-Gate Diagnostic** — carry-forward now PROMOTED to winner. Replaced itself.
- **Lead Source Analytics GH #409** — queued but loop stalled (GH #399 + #403 pending). Will execute when pipeline restores. No subconscious action needed until then.
- **G3 Voice Scope Completion** — ~40% remaining: booking integration, per-tenant provisioning, minutes metering, calls dashboard. Not revenue-immediate vs referral activation. Park until referral + booking funnels fully operational.

## Rejected This Run

- **Booking Conversion Rate metric in weekly funnel report** — loop stalled, new ai-ready issue would queue not execute.
- **G3 Voice scope GH issue as winner** — not revenue-immediate. Referral activation is higher leverage first mover.
- **Day-2 GH #403 comment as winner** — Step 9D handles escalation for #399 daily. #403 comment is real but is bonus action, not winner-class recommendation.

## Questions for Next Run (Run 90)

1. Was the Referral Reward GH issue filed? What did human find on the checklist?
2. Has `REFERRAL_REWARD_ENABLED=1` been set in Railway?
3. If activated: have any referrals been attributed yet? First referral lead?
4. Has human investigated GH #412 and commented with booking_enabled results?
5. Are Keys Koffee business hours now configured?
6. Have GH #399 + #403 been resolved? Is issue-to-pr-loop running again?
