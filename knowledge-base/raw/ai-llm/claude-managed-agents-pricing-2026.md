---
title: Claude Managed Agents Pricing — Complete Breakdown 2026
date: 2026-08-03
source_url: https://www.truefoundry.com/blog/claude-managed-agents-pricing
fetched_at: 2026-08-25
category: ai_llm
tags: [anthropic, managed-agents, pricing, session-hours, claude-opus-5, cost]
---

# Claude Managed Agents Pricing: A Complete Breakdown for 2026

**Published:** August 3, 2026 · Author: Sahajmeet Kaur

## Pricing Structure

Two-component billing model:

1. **Token costs** at standard Claude API rates (input, output, cache write/read)
2. **Session runtime fee:** $0.08 per active session-hour

Idle time is free — charges accrue only while sessions are in a `running` state.

### Pricing by Model

| Model | Input | Output | 5-Min Cache Write | Cache Read |
|-------|-------|--------|-------------------|------------|
| Claude Opus 5 | $5/MTok | $25/MTok | $6.25/MTok | $0.50/MTok |
| Claude Sonnet 5 (through Aug 31, 2026) | $2/MTok | $10/MTok | $2.50/MTok | $0.20/MTok |
| Claude Sonnet 5 (from Sep 1, 2026) | $3/MTok | $15/MTok | $3.75/MTok | $0.30/MTok |
| Claude Haiku 4.5 | $1/MTok | $5/MTok | $1.25/MTok | $0.10/MTok |
| Session Runtime (all models) | $0.08 per active session-hour | — | — | — |

## What's Included vs Extra

Free: idle session time; code execution (folded into session runtime).

Not included: Batch API discounts (50% off unavailable), fast mode pricing multipliers, data residency discounts, web search ($10 per 1,000 searches).

## Worked Example

One-hour coding session on Claude Opus 5:

| Line Item | Calculation | Cost |
|-----------|-------------|------|
| Input tokens | 50,000 × $5/1M | $0.25 |
| Output tokens | 15,000 × $25/1M | $0.375 |
| Session runtime | 1.0 hour × $0.08 | $0.08 |
| **Total** | — | **$0.705** |

## Claude Managed Agents vs Self-Hosted Harness

| Dimension | Claude Managed Agents | Self-hosted (TrueFoundry) |
|-----------|----------------------|---------------------------|
| Framework cost | Included in usage pricing | Open source — no license fee |
| Runtime fee | $0.08/active session-hour | None; own infrastructure |
| Model support | Claude only | 1,000+ LLMs via unified API |
| Deployment | Anthropic-managed US cloud | Self-hosted, on-prem, managed SaaS |
| Governance | Per-tool permission policies | Centralized model-level RBAC & budgets |
| Observability | Server-side event history | OpenTelemetry to Grafana/Datadog |

## Key Takeaways

- Token spend remains the dominant cost driver
- Session runtime adds up quickly at multi-agent scale
- Several API discounts don't carry over to managed sessions
- Large multi-model deployments avoid per-session fees by self-hosting
