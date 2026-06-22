---
type: decision
decision_date: 2026-06-15
status: active
tags:
  - decision
  - pricing
source_status: source-backed
confidence: medium
---

# Decision: Reprice to chatbot / agent_os

## Decision
Collapse the plan lineup to two current paid plans: **`chatbot` $19.99/mo** (widget/chat only)
and **`agent_os` $99.99/mo** (full platform). `free` becomes an internal lapsed/no-subscription
state, never sold. Legacy `growth/autopilot/professional/enterprise` are grandfathered;
`foundation/operations` are retired names never to be used.

**Customer-facing display names** (confirmed via GitHub smoke pass 2026-06-22): `chatbot` is
marketed as **"AI Front Desk"** and `agent_os` as **"AI Workforce"**. Source: [[connector-github-issues]]

## Rationale
Simplify the offer to a clear good/better split aligned to the two product tiers.

## Consequences
- Canonical source: `backend/services/stripe_service.py` + `ai_usage_guard.PLAN_BASELINE_TOKENS`.
- **Drift risk (open):** older docs (canonical-schema, gap-analysis) and possibly the
  BillingPage / Home FAQ still show old prices → see [[Align Pricing Across Surfaces]].

## Confidence
- Medium — CLAUDE.md states this as canonical, but multiple surfaces still disagree (drift
  flagged in [[planning-gap-analysis-2026-06-10]]).

## Related
- [[AgentNexLiFy]] · [[Align Pricing Across Surfaces]]

## Provenance
- [[repo-agentnexlify-claude-md]] · [[planning-gap-analysis-2026-06-10]] · [[dev-knowledge-canonical-schema]] · [[connector-github-issues]]
