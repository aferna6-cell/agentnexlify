# Improvement Backlog — 2026-07-21

## Active

- **Fix Step 9F execution gap**: Add KB staleness bash block to `scripts/daily/nightly-commit-review.sh`. Step 9F in SKILL.md fires only in interactive sessions; automated cron runs the shell script. KB is 8 days stale (threshold: 7 days). Single bash block addition, zero schema changes.

## Parking Lot (survived debate but not chosen)

- **Post GH #399 resolution runbook comment** — add exact 3-step token-rotation instructions to GH #399 via mcp__github__add_issue_comment. Zero code changes. 30 ai-ready issues blocked Day 17. Survived debate. Not chosen because Step 9F monitoring gap is more systemic; GH #399 is a human action item that this subconscious run's notification will surface.
- **Referral analytics dashboard** — add referral_code distribution chart to LeadAttributionPage now that GH #413 (REFERRAL_REWARD_ENABLED) is live. Survived debate (weakened). Medium effort (new frontend page + backend endpoint). Parking until referral data accumulates for 3-5 days post-activation.
- **Add `check_pending_migrations()` to loop_health_scan** — surface silent no-ops from unapplied migrations 180-182 (pending_automations, kb_article_provenance, conversation_message_memory). Not debated top-3 but evidence strong from today's nightly log.
- **Add `/api/admin/integrations/vault-status` endpoint** — gate migration 176 apply-readiness behind a programmatic check for INTEGRATIONS_ENC_KEY. Not debated top-3 but irreversible migration risk is real.

## Rejected This Run

None — all ideas that entered debate survived. Ideas 3 and 5 were not debated (ranked below top 3) but are valid candidates for future runs.

## Questions for Next Run

1. Did the Step 9F bash block get added to `scripts/daily/nightly-commit-review.sh` by the nightly? Check nightly log 2026-07-22 for "Step 9F:" text.
2. Is GH #399 (autopilot-loop token expired) still open? If Day 20+, escalate with P0 label.
3. Referral analytics: after 3-5 days post GH #413 activation, check `leads` table for non-null `referral_code` values. If >0 leads, prioritize referral dashboard.
4. Migrations 180-182: are they applied? Check nightly log or Supabase MCP for table existence.
5. Is mcp_client.py now wired (run 100 winner, PR #537)? If PR merged, verify in os_thread_runner.py imports.
