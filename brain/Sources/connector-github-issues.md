---
type: source
source_id: connector-github-issues
origin: connector
connector: GitHub
account: aferna6-cell
repo: aferna6-cell/agentnexlify
accessed: 2026-07-14
last_refresh: 2026-07-14T09:18Z
sensitivity: normal
tags: [source, connector]
---

# Source: GitHub issues/PRs (auto-refreshed)

## What this is
Live snapshot from `refresh_connectors.py` of `aferna6-cell/agentnexlify`.

## Counts (as of 2026-07-14T09:18Z)
- Open issues: 109
- Open PRs: 31
- Recent closed issues sampled: 10

## Top open issues (non-digest)
  - #415 ACTION REQUIRED: Keys Koffee — add business hours to enable bookings (Day 20, 0 bookings since launch)
  - #414 ACTION REQUIRED: Collect Keys Koffee business hours — 3rd tenant blocked on booking
  - #413 ACTION REQUIRED: Activate referral reward — Migration 162 in prod, one env-var flip
  - #412 ACTION REQUIRED: Booking funnel diagnostic — 0 real bookings 18 days after launch
  - #407 nightly-review [HIGH]: Referral reward Stripe webhook — verify before enabling REFERRAL_REWARD_ENABLED
  - #406 KB auto-populate blocked: set ANTHROPIC_API_KEY as an Actions secret [human-action-required]
  - #403 Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot loop AND KB autopopulate [human-action-required]
  - #399 autopilot-issue-loop GitHub Actions failing 5+ days — AUTOPILOT_GH_TOKEN expired [CRITICAL]
  - #394 Fix brain-refresh[bot] credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN missing [MEDIUM]
  - #392 Brain refresh connectors failing for 4+ consecutive days (GitHub 403, Supabase token missing)
  - #330 Human legal review: TermsOfService section 4 rewritten (payment terms + failed-payment clause)
  - #329 Apply migration 154 (conversation sentiment + intent) to production
  - #293 MEDIUM: orchestrator + billing_reconciliation use stale plan names after repricing
  - #292 MEDIUM: sms_rate_limiter + api_key_auth missing new plan names (chatbot/agent_os)
  - #266 security: finish integrations-secret encryption — backfill + sunset plaintext columns

## Notes
- Autonomous-dev cadence: morning-digest / nightly-commit-review / subconscious loop.
- Regenerated automatically; edits here will be overwritten on next refresh.
