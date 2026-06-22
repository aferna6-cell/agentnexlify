---
type: map
name: "GitHub Activity"
tags:
  - map
  - moc
last_updated: 2026-06-22
---

# GitHub Activity

Snapshot of `aferna6-cell/agentnexlify` (2026-06-22). Refreshable via
[[Refresh The Brain]] (`_tools/refresh_connectors.py`).

## Now
- ~84 open issues (many are automated `digest` entries), ~50 open PRs (lots of stale Dependabot
  + feature branches). Source: [[connector-github-issues]]
- Active blockers: see [[Open Loops]] (#263, #329, #330, #266, PR #333).

## History (shipped)
- ~85 merged PRs (#164→#336); 36 substantive closed issues (2026-04-21→2026-06-15).
  Full themed breakdown: [[connector-github-history]].
- Major arcs: two-plan repricing, Agent OS becoming the product spine, onboarding/activation
  funnel, secrets-at-rest, leadgen/outreach.

## How the repo runs
- Mostly AI-authored via [[Autonomous Dev Operation]] (morning-digest, nightly-commit-review,
  subconscious loop).

## Recurring problems
- Plan-name drift after repricings · silent-failure bugs · Stripe webhook idempotency ·
  migration/schema drift · CI Actions-minute exhaustion. Detail: [[connector-github-history]].

## Related
- [[Autonomous Dev Operation]] · [[Open Loops]] · [[Decision Log]]
