---
type: map
name: "Open Loops"
tags:
  - map
  - moc
last_updated: 2026-06-22
---

# Open Loops

Unfinished work + blockers (business scope). Ordered by priority.

## High
- [[Insurance Quote for Launch]] — the only HIGH-severity launch blocker (owner phone call). Confirmed 2026-06-23 as the single rubric zero that flips NO-GO → GO.
- [[Align Pricing Across Surfaces]] — owner decision + alignment pass (G5).
- [[Convert Beta Tenants to Paid]] — revenue priority (led by [[MTOptions]]).
- ~~[[Weekly Value Digest]]~~ — G2 retention lever. **Shipped 2026-06-23**: the Friday emailer already existed; added dollar-framed estimated pipeline `$`, configurable `avg_lead_value` (graceful when column absent, no migration), conversations count, + 23 tests. `backend/services/weekly_value.py` + `scheduled_jobs_ext.py`.

## Medium
- [[Connect Public Domain]] — repoint agentnexlify.com to the live Vercel project.
- [[Proactive AI Opportunities Job]] — nightly proactive suggestions (G7).

## Infra / hygiene (from sources, not yet broken out)
- Log retention/sink, uptime monitor, status page, Sentry OAuth (rubric). Source: [[planning-launch-readiness-rubric]]
- OAuth creds pending: Google Business Profile, social, real SERP. Source: [[eng-memory-blocked-items]]
- Untracked deps (no requirements.txt entries) — reproducibility risk. Source: [[eng-memory-blocked-items]]

## From GitHub (smoke pass 2026-06-22, corrected 2026-06-23)
- **#263** — NOT 24 pending migrations. **2026-06-23 object-existence audit: real pending = 2**, both SAFE-IDEMPOTENT `ADD COLUMN IF NOT EXISTS` (`117_zapier_api_keys`, `129_chat_messages_os_mirror`). The bogus "24" came from `005`/`007` duplicate-numbered files breaking number-keyed diff tooling + the Supabase migration-history table only recording 112/157 files (rest applied out-of-band). Prod-apply owner-gated; downgrade from CRITICAL. Source: `audits/audit-schema-drift-2026-06-23.md`
- **#329** — apply migration 154 (conversation sentiment + intent) to production.
- **#330** — human legal review of TermsOfService §4 (payment terms).
- **#266** — finish integrations-secret encryption (backfill + sunset plaintext).
- KB embeddings broken since ~2026-04-30: root cause = missing `VOYAGE_API_KEY` (owner-gated) **plus** no graceful degradation in `backend/services/embeddings.py:34,52,70` (hard 401 raise) + the cron compile path swallows the crash as success. Code patch drafted (not applied). Source: `audits/audit-kb-embeddings-2026-06-23.md`
- Recently fixed overnight: #308 (webhook idempotency), #292/#293 (stale plan names).

## Review 2026-06-23 — 4-lane foundation/launch pass
- **Launch rubric correction:** `brain/Projects/Paid Launch Readiness.md` mislabeled Sentry (4.2) + uptime (4.3) as zeros — both already **scored 1** in `planning/launch-readiness-rubric.md` (code shipped: Sentry `main.py:135-146`, uptime workflow + probe; only owner secrets pending). Real rubric **0s = 4.5 log retention, 7.5 status page, 8.5 case study, 9.5 outreach, 10.6 insurance**.
- **7.5 status page — built 2026-06-23**: new `backend/routers/status_page.py` (`/status` + `/status.json`, no auth/no tenant scope, 503 when degraded). Gives the uptime monitor a clean public JSON target.
- Remaining buildable zeros are owner-gated content/secrets: 4.5 needs a log-sink account, 8.5 needs partner+MTOptions consent, 9.5 is owner-authored sales copy.
- Source: `audits/audit-launch-readiness-2026-06-23.md`

## Related
- [[Paid Launch Readiness]] · [[Paid Launch Readiness Pack]] · [[Autonomous Dev Operation]]
