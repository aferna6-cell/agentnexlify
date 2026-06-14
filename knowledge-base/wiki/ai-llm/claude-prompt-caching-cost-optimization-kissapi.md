---
title: "Claude Prompt Caching — Cost Optimization Without Model Downgrade"
category: ai-llm
tags: [claude-api, prompt-caching, cost-optimization, ephemeral-cache, cache-hit-rate, anthropic-beta]
sources:
  - https://kissapi.ai/blog/claude-prompt-caching-api-cost-optimization-2026.html
created: 2026-04-28
updated: 2026-04-28
summary: "Prompt caching cuts Claude input cost 40-70% by reusing stable prefixes; hit-rate math (30%→74% cost, 70%→40%, 90%→23%) is the entire pitch."
---

Prompt caching is the cheapest Claude optimization that does not touch model quality. The mechanic is plain: mark a stable prompt block with `cache_control: {"type": "ephemeral"}`, and subsequent requests re-read those tokens from cache instead of re-billing them as fresh input. KissAPI's March 2026 cost-optimization guide puts concrete numbers on the move — a 9,000-token instruction prefix paired with a 1,500-token user payload drops from 100% input cost to 23% effective input cost at a 90% hit rate. That is not a downgrade trick; the same model serves the same user with a smaller bill.

The win lives upstream of inference. Most teams overpay because every request re-sends the same policy text, style guide, schema notes, and tool descriptions. Hit rates of 30% land effective cost near 74%, 70% lands near 40%, 90% lands near 23%. The leverage is the stability of the cached prefix — once you stop letting timestamps, request IDs, and per-user data leak into the cached block, the rest is straight savings. That is why this pairs with the broader cost discipline already pinned in [[claude-api-pricing-breakdown-2026]] and [[claude-opus-4-7-tokenizer-cost-reality-2026]].

The integration is small. The Messages API call needs two headers — `anthropic-version: 2023-06-01` and the prompt-caching beta `anthropic-beta: prompt-caching-2024-07-31` — plus a `cache_control` annotation on the system block (or any reusable text block) that should be cached. A `usage` object on the response surfaces `cache_creation_input_tokens` (first-time write) and `cache_read_input_tokens` (subsequent reads), which is where you measure actual hit rate per endpoint. Without those metrics, you are flying blind on whether caching is doing anything.

KissAPI's Python pattern adds one move worth stealing: a versioned prefix tag (`[review-v3] You are a backend reviewer...`). The version string lives inside the cached block on purpose. When you tweak instructions, you bump the version and let the new prefix earn fresh cache entries, instead of mystery-mixing two policy versions across worker pods. That eliminates one of the more common bugs in caching rollouts — phantom drift where one request followed `v3` and the next followed `v4` and nobody can reproduce the difference.

The same paper enumerates the seven standard mistakes: caching tiny prompts (sub-500 tokens, savings too small), mixing personalization into system text (kills hit rate by uniqueness), ignoring the usage fields (no measurement), and skipping a fallback route (cost optimization is not reliability). The vendor framing for the fallback move was a KissAPI-specific OpenAI-compatible secondary endpoint, but the underlying point is portable — the cached endpoint is still one upstream provider, and burst-traffic or regional incidents need a planned alternate path.

For AgentNexLiFy, this is most relevant on the FastAPI calls in `backend/services/llm_runtime.py` and the advisor/executor stack in `backend/services/advisor_executor.py`. The advisor brief workload has a stable system prompt and a stable role/tools envelope; only the task description changes per call. The same is true for the per-tenant chat widget once a tenant's knowledge-base block stabilises — that block is the natural cached prefix, dynamic tenant facts (caller name, recent thread context) live in the volatile user message. Hit rate goes up the moment per-call randomness moves out of the system text. The 30%-of-input rule of thumb (only cache when ≥30% of request tokens are reused across many calls) fits cleanly with our existing usage pattern.

## Key Concepts

- **Ephemeral cache** — Anthropic's prompt-cache primitive activated by `cache_control: {"type": "ephemeral"}` on a content block, with a 5-minute TTL refresh on every hit.
- **Cache hit rate** — fraction of input tokens served from cache; the only number that matters when judging whether caching is helping.
- **`cache_creation_input_tokens` / `cache_read_input_tokens`** — usage fields exposed on the Messages API response; first writes vs subsequent reads.
- **Stable prefix** — the portion of a prompt that does not vary per call (system instructions, policy, schema, tool definitions); the only thing worth caching.
- **Versioned prompt tag** — embedding a string like `[review-v3]` inside the cached block so prompt evolutions earn fresh cache entries on purpose.
- **Anthropic beta header** — `anthropic-beta: prompt-caching-2024-07-31`; required to enable the feature on the Messages API.
- **30% rule** — heuristic that caching pays off when the stable prefix is at least 30% of total request input and is reused across many calls.

## Related Articles

- [[claude-prompt-caching-5min-ttl-2026]] — TTL refresh mechanics and 5-minute window behaviour, complements the cost math here.
- [[claude-api-pricing-breakdown-2026]] — full per-token Claude pricing context for sizing the savings.
- [[claude-opus-4-7-tokenizer-cost-reality-2026]] — 4.7's tokenizer change can move the same text up to 1.35x more tokens, so caching matters even more on Opus 4.7.
- [[anthropic-managed-agents-cowork-ga-april-2026]] — Managed Agents share the same caching mechanics for advisor/executor flows.

## Relevance to AgentNexLiFy

`backend/services/llm_runtime.py` is the single shared call site to add `cache_control` annotation. Every advisor brief, every widget reply, every Lead Qualifier classification rides through it. Wiring caching there once captures the savings across all current and future Managed Agents.

Concrete next moves:
1. Add a `system_prefix` parameter to the runtime that injects the policy/role text as a `cache_control: {"type": "ephemeral"}` block, and require a `prefix_version` tag string for cache-busting hygiene.
2. Log `cache_creation_input_tokens` and `cache_read_input_tokens` from `response.usage` into the existing per-call telemetry, alongside model + duration. Without those numbers we cannot prove the optimization is working per `usage-observability.md`.
3. For the advisor pass specifically (Opus 4.7, ~300-1,200 output tokens), the system block is small enough that caching savings are marginal — measure first before adding complexity. The bigger win is the executor pass with full tool descriptions in the prefix.
4. For the per-tenant widget chat, the tenant knowledge-base block is the natural cached prefix once the per-tenant content stabilises; today the KB block is rebuilt per call, which is exactly the bug this guide warns about. Pin the KB block format and let the cache absorb it.

Cost ceiling for AgentNexLiFy: at 70-90% hit rate on the executor stable prefix, expected reduction is 40-77% of input cost on those calls. Sized against current monthly Anthropic spend, this is the highest-ROI optimization on the table that does not require changing model tier.
