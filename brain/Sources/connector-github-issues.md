---
type: source
source_id: connector-github-issues
origin: connector
connector: GitHub
account: aferna6-cell
repo: aferna6-cell/agentnexlify
accessed: 2026-07-11
last_refresh: 2026-07-11T09:00Z
sensitivity: normal
tags: [source, connector]
---

# Source: GitHub issues/PRs (auto-refreshed)

## What this is
Live snapshot from `refresh_connectors.py` of `aferna6-cell/agentnexlify`.

## Counts (as of 2026-07-11T09:00Z)
- Open issues: 107
- Open PRs: 31
- Recent closed issues sampled: 6

## Top open issues (non-digest)
  - #409 feat(analytics): add lead source breakdown chart to analytics page
  - #408 nightly-review [MEDIUM]: landing-page-v2/widget modified — violates CLAUDE.md "do not touch" rule
  - #407 nightly-review [HIGH]: Referral reward Stripe webhook — verify before enabling REFERRAL_REWARD_ENABLED
  - #406 KB auto-populate blocked: set ANTHROPIC_API_KEY as an Actions secret [human-action-required]
  - #403 Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot loop AND KB autopopulate [human-action-required]
  - #399 autopilot-issue-loop GitHub Actions failing 5+ days — AUTOPILOT_GH_TOKEN expired [CRITICAL]
  - #394 Fix brain-refresh[bot] credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN missing [MEDIUM]
  - #392 Brain refresh connectors failing for 4+ consecutive days (GitHub 403, Supabase token missing)
  - #385 Add SMS Compliance Dashboard (backend router + frontend page)
  - #330 Human legal review: TermsOfService section 4 rewritten (payment terms + failed-payment clause)
  - #329 Apply migration 154 (conversation sentiment + intent) to production
  - #293 MEDIUM: orchestrator + billing_reconciliation use stale plan names after repricing
  - #292 MEDIUM: sms_rate_limiter + api_key_auth missing new plan names (chatbot/agent_os)
  - #266 security: finish integrations-secret encryption — backfill + sunset plaintext columns
  - #265 deps: re-raise the fastapi <0.136 cap once starlette is bumped to a 0.50-compatible release

## Notes
- Autonomous-dev cadence: morning-digest / nightly-commit-review / subconscious loop.
- Regenerated automatically; edits here will be overwritten on next refresh.
