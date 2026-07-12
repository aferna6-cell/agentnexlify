# Improvement Backlog — 2026-07-12

## Active

- **Create `.github/workflows/secrets-health-check.yml`** — zero-dependency weekly workflow that
  validates ANTHROPIC_API_KEY + AUTOPILOT_GH_TOKEN are set and live using GITHUB_TOKEN; files alert
  issue if missing. Closes the self-referential monitoring gap in Step 9E. (Run 90 winner, S effort)

## Parking Lot (survived debate or deferred)

- **Add Step 9F — Booking Conversion Tracker** — nightly step that checks GH #412 for human
  comments + tries backend REST API for booking count; alerts on first real booking. Condition: file
  once backend API mechanism for unauthenticated count endpoint confirmed. (Run 91 candidate)

- **Keys Koffee Business Hours GH Issue** — email template for owner to send to Keys Koffee tenant
  requesting business hours. Unblocks 3rd booking tenant. XS effort. (Bonus Action this run)

- **Diagnose Supabase MCP availability in headless sessions** — investigate `.mcp.json` config for
  why `mcp__supabase__execute_sql` isn't available in nightly/subconscious headless runs. High
  multiplier if fixed. (Run 91-92 candidate, M effort)

- **Lead Source Analytics** — GET /api/leads/source-breakdown + BarChart in AnalyticsPage.jsx.
  GH #409 queued. Will auto-execute when issue-to-pr-loop restores (#399/#403 resolved). 83-run
  parking lot.

- **Week-1 Retention Follow-up Automation Template** — custom automation template for
  post-service follow-ups (customer-gaps.md open gap, M effort). Revisit after pipeline restored.

- **Weekly Revenue Digest Morning Step** — consolidated weekly revenue status issue (leads,
  bookings, referral, P0 actions). (Run 91-92 candidate if pipeline stall persists)

## Rejected This Run

- **Step 9F as winner** (WEAKENED → parking lot) — valid but lower structural leverage than
  secrets health-check. Mechanism complexity (backend API auth) not fully resolved.

- **Keys Koffee hours GH issue as winner** (WEAKENED → Bonus Action) — valid, lower leverage
  than solving 8-day pipeline root cause. Queue fatigue risk real (5 pending issues already).

- **Weekly Revenue Digest as winner** (not debated → parking lot) — owner might need fewer issues,
  not more. Consolidation helps but doesn't fix underlying inaction pattern.

## Questions for Next Run (Run 91)

1. Did secrets-health-check.yml detect the current ANTHROPIC_API_KEY gap on first run?
2. Has owner acted on either #399 or #403 (7-min combined fix)?
3. Is the pipeline (issue-to-pr-loop + kb-autopopulate) restored after secrets are set?
4. Keys Koffee — tenant provided hours yet?
5. Step 9F: is there a read-only backend API endpoint we can use without Supabase MCP?
