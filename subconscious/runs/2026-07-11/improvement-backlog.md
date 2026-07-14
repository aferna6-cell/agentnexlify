# Improvement Backlog — Run 88 (2026-07-11)

## Active

- **File "Booking Funnel Diagnostic" GH issue** — package booking_enabled + tenant_availability SQL queries for human execution. Labels: revenue, human-action-required, diagnostic. Answers 0-bookings mystery. AUTONOMOUS-EXECUTABLE via GitHub MCP. (run 88 winner)

## Parking Lot (survived debate but not chosen)

- **Diagnose Supabase MCP availability in headless sessions** — nightly and subconscious sessions both lack Supabase MCP despite org-level install. Fix enables Steps 9F+ and future autonomous DB diagnostics. Blocked by SUPABASE_ACCESS_TOKEN unknown state (#394). (run 89 candidate)
- **Add Step 9F to nightly SKILL.md — tenant availability hours check** — secondary booking-funnel hypothesis. Add after human confirms booking_enabled=true for all real tenants. Schema to confirm first. (run 89 candidate, conditional on booking_enabled=true result)
- **P0 Day 7 escalation comment on GH #399** — add Day 7 status + 40-issue queue count. Bonus action, not winner (Step 9D already does daily comments). Also verify GH #403 (ANTHROPIC_API_KEY) exists with critical labels.
- **Referral Reward Pre-Gate Diagnostic** — check if referral rewards are gated behind agent_os-only plan, excluding chatbot tier users. Parking lot carry-forward from run 87.
- **Lead Source Analytics GH #409** — will be picked up by issue-to-pr-loop once GH #399 + #403 resolved. No subconscious action needed.

## Rejected This Run

- **Pipeline dual-blocker P0 escalation as winner** — WEAKENED: Step 9D automated channel already covers this. Subconscious filing a second escalation issue adds noise, not signal. Better as bonus action.
- **Step 9F as winner** — WEAKENED: premature (schema unverified + Supabase MCP blocked + hypothesis A unconfirmed). Right idea, wrong timing.

## Questions for Next Run (Run 89)

1. Did the human run the Booking Funnel Diagnostic SQL? What did they find?
2. Is booking_enabled=true or false for MTOptions, 914 Exterior, Keys Koffee?
3. Has GH #399 (AUTOPILOT_GH_TOKEN) been resolved? Is the issue-to-pr-loop running again?
4. Has GH #403 (ANTHROPIC_API_KEY in Actions) been filed with correct labels?
5. Is SUPABASE_ACCESS_TOKEN now set in Railway Variables (#394)?
6. If booking_enabled=true + no availability rows: which tenant_availability schema is in use? (`id`, `client_id`, `day_of_week`, `start_time`, `end_time`?) Needed to write Step 9F.
