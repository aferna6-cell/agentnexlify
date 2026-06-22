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
- [[Insurance Quote for Launch]] — the only HIGH-severity launch blocker.
- [[Align Pricing Across Surfaces]] — owner decision + alignment pass (G5).
- [[Weekly Value Digest]] — highest open product gap (G2), retention lever.
- [[Convert Beta Tenants to Paid]] — revenue priority (led by [[MTOptions]]).

## Medium
- [[Connect Public Domain]] — repoint agentnexlify.com to the live Vercel project.
- [[Proactive AI Opportunities Job]] — nightly proactive suggestions (G7).

## Infra / hygiene (from sources, not yet broken out)
- Log retention/sink, uptime monitor, status page, Sentry OAuth (rubric). Source: [[planning-launch-readiness-rubric]]
- OAuth creds pending: Google Business Profile, social, real SERP. Source: [[eng-memory-blocked-items]]
- Untracked deps (no requirements.txt entries) — reproducibility risk. Source: [[eng-memory-blocked-items]]

## From GitHub (smoke pass 2026-06-22)
- **#263** — 24 pending migrations (CRITICAL, schema drift). Source: [[connector-github-issues]]
- **#329** — apply migration 154 (conversation sentiment + intent) to production.
- **#330** — human legal review of TermsOfService §4 (payment terms).
- **#266** — finish integrations-secret encryption (backfill + sunset plaintext).
- **PR #333** — 51-commit "main-pending" batch, stale 4+ days, needs review/merge.
- KB embeddings broken since ~2026-04-30 (missing `VOYAGE_API_KEY`). Source: [[connector-github-issues]]
- Recently fixed overnight: #308 (webhook idempotency), #292/#293 (stale plan names).

## Related
- [[Paid Launch Readiness]] · [[Paid Launch Readiness Pack]] · [[Autonomous Dev Operation]]
