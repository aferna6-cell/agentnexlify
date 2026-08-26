---
title: Anthropic Managed Agents — Pricing and Real Costs Explained
date: 2026-06-10
source_url: https://www.opslyft.com/blog/anthropic-managed-agents
fetched_at: 2026-08-26
category: ai_llm
tags: [anthropic, managed-agents, pricing, session-hours, cost-control, opus-4-8, sonnet-4-6, haiku-4-5]
---

# Anthropic Managed Agents: Pricing and Real Costs Explained

*Author: Khushi Dubey (OpsLyft). Updated 10 Jun 2026. Managed Agents entered public beta April 2026; pricing is beta pricing and may change.*

## Three billing axes

1. **Tokens** — standard per-model rates. Haiku 4.5 $1 / $5 per MTok (in/out); Sonnet 4.6 $3 / $15; Opus 4.8 $5 / $25. Prompt caching discounts apply.
2. **Session runtime** — **$0.08 per session-hour**, metered in milliseconds, charged only while the session is actively running. Idle sessions are free.
3. **Tools** — e.g. web search $10 per 1,000 searches. Custom tools you host cost nothing from Anthropic.

## Worked example (from article)

One-hour Opus 4.8 session, 50k input tokens, 15k output tokens:

| Component | Uncached | 80% cache hit |
|---|---|---|
| Input | $0.25 | ~$0.07 |
| Output | $0.375 | $0.375 |
| Runtime (1h) | $0.08 | $0.08 |
| **Total** | **$0.705** | **$0.525** |

Runtime is ~11% of the bill. Tokens dominate; model choice and caching are the levers.

## What is NOT available on Managed Agents

- Batch API 50% discount
- Fast mode
- `inference_geo` regional multiplier
- Bedrock / Vertex — direct Anthropic API only

## Feature set

- Sandboxed execution environment per session
- Long-running sessions with checkpointing/resume
- Governance: tracing, per-agent attribution, audit
- Multi-agent orchestration + self-evaluation (research preview)

## Cost-control playbook

- **Route by difficulty** — Haiku for classification/extraction, Sonnet for standard agent turns, Opus only for planning/hard reasoning.
- **Cache aggressively** — stable system prompt + tool defs + KB context above the breakpoint.
- **Release idle sessions** — idle is free, but forgotten active loops are not.
- **Budget tool calls** — web search at $10/1k adds up in research loops.
- **Per-agent attribution** — tag sessions so you can see which agent burns spend.

## Anecdotes cited

- A weekend runaway agent loop cost one team **$4,200**.
- A SaaS company cut Managed Agents spend from **$87k → $24k/mo (72%)** by routing by difficulty instead of defaulting to Opus.

## Notes for AgentNexLiFy

- Confirms session-hour pricing already recorded in `wiki/ai-llm/claude-managed-agents-session-hour-pricing-2026.md`; adds the "not available" list (no Batch, no fast mode) and the 72% routing anecdote.
- Our `managed_agents.build_budget(cents)` session budget (see `.claude/rules/task-budgets.md`) is the hard stop against the $4,200 runaway pattern — keep it on every script-launched session.
- Lead Qualifier on Haiku, not Opus, is the right default per the routing math.
