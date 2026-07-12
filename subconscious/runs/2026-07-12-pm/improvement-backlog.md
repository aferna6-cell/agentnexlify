# Improvement Backlog — Run 90 (2026-07-12-pm)

## Active (pending human action)

| Run | Idea | Category | Effort | Status |
|-----|------|----------|--------|--------|
| 89 | Activate referral reward — GH #413 filed, UX checklist remaining | customer_value | XS | pending_human_action |
| 88 | Booking funnel diagnostic — GH #412 filed, human SQL needed | customer_value | XS | pending_human_action |
| 85 | Lead Source Analytics dashboard — GH issue + ai-ready label, awaiting loop | customer_value | L | pending_autonomous (blocked: #399/#403) |

## Parking Lot

| Idea | Category | Effort | Why Parked |
|------|----------|--------|------------|
| Keys Koffee booking escalation GH issue | customer_value | XS | GH #412 covers booking diagnosis; Keys Koffee is noted there. File Keys Koffee-specific issue if GH #412 has no human action by run 92. |
| Booking health watchdog (feat: email tenant if booking_enabled=true but 0 slots after 3 days) | code_health | M | Forward-looking preventive feature. Appropriate for issue-to-pr-loop once #399/#403 resolved. |
| Reward redemption path code audit — confirm Stripe credit vs manual credit vs email | customer_value | XS | Sub-task of GH #413 checklist. Run 91 candidate if #413 still no human action. |
| Day-9+ escalation on GH #399 + #403 | operational | XS | Run 91 candidate if still open. |

## Rejected / Frozen

| Idea | Why |
|------|-----|
| ai_human_handoff | FROZEN — governance.json frozen_ideas list |
| Widget drift | RETIRED run 70 — human-only task |
| Any direct Supabase MCP query | BLOCKED — Supabase MCP unavailable in headless sessions (confirmed runs 87-88) |
