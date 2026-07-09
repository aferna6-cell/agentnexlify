---
type: map
name: "GitHub Activity"
tags:
  - map
  - moc
last_updated: 2026-07-01
---

# GitHub Activity

Snapshot of `aferna6-cell/agentnexlify` (2026-07-01). Refreshable via
[[Refresh The Brain]] (`_tools/refresh_connectors.py`).

## Now
- Connector refresh DEGRADED: 2026-07-01 runs hit `HTTP 403` on GitHub and skipped Supabase
  (`SUPABASE_ACCESS_TOKEN` not set in Actions secrets) — connector sources last good 2026-06-22.
  Source: `INGESTION-LOG.md` tail.
- Active blockers: see [[Open Loops]] (#330, #266, SMS Compliance Dashboard, Zapier #107).

## History (shipped)
- ~120 merged PRs (#164→#371); 36 substantive closed issues (2026-04-21→2026-06-15).
  Full themed breakdown: [[connector-github-history]].
- Major arcs: two-plan repricing, Agent OS becoming the product spine, onboarding/activation
  funnel, secrets-at-rest, leadgen/outreach.
- 2026-06-22→07-01 highlights: 12-PR GTM/conversion session (#360–#371 — funnel analytics,
  referral attribution end-to-end, 13-vertical KB moat + SEO pages, tenant health + churn-watch,
  kill-trial); LLM Council 9 SMB fixes incl. TCPA opt-out suppression (2026-06-26); KB
  autopopulate fixed after ~58-day silent gap (2026-06-30); Vercel free-tier deploy quota
  exhausted by the 11-PR day, frontend deploys blocked ~24h (2026-06-23).

## How the repo runs
- Mostly AI-authored via [[Autonomous Dev Operation]] (morning-digest, nightly-commit-review,
  subconscious loop).

## Recurring problems
- Plan-name drift after repricings · silent-failure bugs · Stripe webhook idempotency ·
  migration/schema drift · CI Actions-minute exhaustion. Detail: [[connector-github-history]].

## Related
- [[Autonomous Dev Operation]] · [[Open Loops]] · [[Decision Log]]
