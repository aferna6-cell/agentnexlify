---
type: source
source_id: connector-github-history
origin: connector
connector: GitHub
account: aferna6-cell
repo: aferna6-cell/agentnexlify
accessed: 2026-06-22
sensitivity: normal
tags: [source, connector, history]
---

# Source: GitHub deep history (closed issues + merged PRs)

## What this is
Deep read-only crawl of `aferna6-cell/agentnexlify` history, 2026-06-22: ~74 closed issues
(36 substantive + 38 automated digests, 2026-04-21→2026-06-15) and ~85 merged PRs (range
#164–#336; substantive work #203→#336), plus 30 most-recent commits.

## What it proves (shipped work, by theme)
- **Billing**: two-plan repricing (#288/#296/#304); remove free tier + gate signup behind
  payment (#291/#298); kill 7-day trial → charge on signup (#322, reversing #299);
  profit-guarantee usage caps + $24.99 usage pack (#303); dunning recovery (#300/#301);
  webhook idempotency fix (#308).
- **Agent OS**: adopt demo framework as core (#203); engine-only cutover (#219); knowledge
  graph migration 133 (#220); gate to agent_os plan (#323); retire 18 standalone pages for
  agent-first UI (#222/#236); new agents — Outbound Outreach (#318), Conversation Insights
  (#312/#315/#316).
- **Onboarding/activation**: signup overhaul + Google OAuth (#137/#235); instant KB from URL
  (#313); interactive /demo + public sandbox (#314/#245); WordPress install plugin (#140/#214).
- **Integrations/security**: encrypt secrets at rest, pgcrypto key vault migration 120
  (#129/#131/#264); Zapier API keys + RLS (#57/#58); SSRF guard consolidation; many
  silent-failure fixes (#97/#99/#109/#94).
- **Leadgen/outreach**: lead engine Places→CSV + cold-email sequences (#334); CAN-SPAM footer;
  OpenStreetMap keyless fallback.

## Decisions surfaced
- Two-plan pivot; remove free tier; kill trial; retire marketing add-on into Agent OS (#228);
  Agent OS as the product spine; centralize SSRF guard; accept reduced CI cadence for
  Actions-minute cost.

## Recurring themes / chronic problems
- Plan-name drift after each repricing (#81/#181/#292/#293).
- Silent-failure bug class (nightly review).
- Launch-readiness grind (191→208→221/262).
- Stripe webhook idempotency/race (#295/#301/#308).
- Migration/schema drift (#259/#261/#230).
- GitHub Actions minutes exhaustion → cron throttling.

## Note
Repo is heavily AI-operated (most commits authored by "Claude") via morning-digest +
nightly-commit-review + a subconscious self-improvement loop. Large payloads were parsed
off-context; all 74 issues + 2 PR pages read in full. Read-only; no mutations.
