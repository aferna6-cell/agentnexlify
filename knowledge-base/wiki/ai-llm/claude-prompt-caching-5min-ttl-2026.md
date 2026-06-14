---
title: "Claude Prompt Caching — 5-Minute TTL and the Architecture Patterns That Survive It"
category: ai-llm
tags: [prompt-caching, claude-api, cost-optimization, ttl, keep-alive, batching, anthropic, sonnet-4-6]
sources: ["raw/ai-llm/dev-to-whoffagents-claude-prompt-caching-in-2026-the-5-minute-ttl-chan.md"]
created: 2026-04-23
updated: 2026-04-23
summary: "Anthropic quietly cut prompt cache TTL from 60 minutes to 5 minutes in early 2026, raising effective Claude API costs 30-60% for cron-paced workloads; keep-alive pings, request batching, and breakeven math are the surviving patterns."
---

# Claude Prompt Caching — 5-Minute TTL and the Architecture Patterns That Survive It

In early 2026 Anthropic cut the Claude prompt cache TTL from 60 minutes to 5 minutes, turning a cost structure that rewarded low-frequency writes into one that punishes them. Workloads engineered for the 60-minute window — cron agents, batch document pipelines, chat sessions with 10+ minute idle gaps — saw effective API costs rise 30-60% overnight because the write premium now amortizes over two reads instead of twenty. The economics of caching did not vanish; they moved. Anything with >10 requests per 5-minute window still benefits. Anything with <2 requests per 5-minute window actively loses money to the write premium. The 2-10 range is the new middle zone where architecture decides whether caching is still worth it.

The mechanics are unchanged. Claude Sonnet 4.6 charges $3.00/M input tokens normally, $3.75/M for cache writes (a 25% premium), and $0.30/M for cache reads (90% discount). Cache blocks require a minimum of 2,048 tokens on Sonnet 4.6 and 4,096 tokens on Opus/Haiku before they qualify. The `cache_control: {type: "ephemeral"}` marker in the messages array is what opts a prefix in. What changed is only the TTL: how long the cached prefix survives after each hit. The 5-minute clock resets on every cache read, so active workloads with sub-5-minute request cadence keep the cache warm indefinitely. Workloads with gaps pay the write premium again on every cold start.

The breakeven math sharpens with the shorter TTL. Caching pays off when reads exceed ~1.3 per write for a typical 10k-token system prompt. Below that threshold, the 25% write premium costs more than the 90% read discount recovers. A 10,000-token system prompt at 1.1 average requests per 5-minute window actually costs more with caching ($0.0756) than without ($0.066). This is exactly the scenario that recurs in low-traffic production apps, staging environments, and idle cron jobs — environments where teams historically assumed caching was free money. The `should_cache` heuristic matters:

```python
def should_cache(prompt_tokens: int, expected_requests_per_5min: float) -> bool:
    write_premium = prompt_tokens * (3.75 - 3.00) / 1_000_000
    read_savings = (expected_requests_per_5min - 1) * prompt_tokens * (3.00 - 0.30) / 1_000_000
    return read_savings > write_premium
```

The first surviving pattern is the **keep-alive ping**. A lightweight request every 4 minutes with `max_tokens=1` resets the TTL clock cheaply. This works for long-lived servers — chat backends, API endpoints — where a persistent process exists to run the keepalive thread. It fails for serverless and cron environments because there is no persistent process. For AgentNexLiFy's widget chat backend (FastAPI on Railway, always-on), the keep-alive pattern is a direct fit; for the nightly commit review and KB auto-populate crons, it is not.

The second pattern is **request batching**. Instead of calling Claude once per incoming item, the worker accumulates items into bursts of N requests tightly in time. Twenty requests within 30 seconds amortize a single cache write over nineteen reads. The `max_batch=20, max_wait_ms=2000` pattern in the source is a standard deque-based batcher. For AgentNexLiFy's `backend/services/automation/scheduled_jobs.py` and the daily KB compile path, batching is more realistic than keepalive — the work arrives in natural chunks anyway, and batching tightens the window.

The third pattern is **reducing cache dependency entirely**. If the workload genuinely averages under 1.3 reads per write, turn caching off. This is counterintuitive because teams think of caching as free savings, but the write premium makes it a net loss below threshold. Measuring the actual hit rate via `response.usage.cache_creation_input_tokens` and `response.usage.cache_read_input_tokens` is the only way to know. A hit rate under 60% combined with a large system prompt is the signal that caching is actively costing money.

The fourth pattern — structural and often overlooked — is **byte-identical prefix ordering**. A single character of drift (a timestamp, a unique ID, a whitespace difference) in the cached prefix creates a total cache miss. System prompts must live at the start of the messages array with `cache_control` markers; any dynamic content (current time, user ID, request-specific context) must appear in the user message, after the cached block. This is how [[effective-context-engineering]] ends up intertwined with caching: the same just-in-time principle that keeps attention budget lean also preserves cache hits.

The broader lesson is that Anthropic can change the TTL unilaterally. The 60-minute era of "caching is free money" is over, and any production workload dependent on long-lived caches is now running on borrowed assumptions. The surviving mental model is: measure hit rate, pick the right pattern (keepalive, batching, or no caching) per call site, and treat the TTL as a platform parameter that will change again.

## Key Concepts

- **Ephemeral cache block** — A prefix in the messages array marked with `cache_control: {type: "ephemeral"}`. Claude hashes this block, serves subsequent identical prefixes from cache at $0.30/M, and charges a 25% premium ($3.75/M) on the first write.
- **TTL reset on hit** — Every cache read resets the 5-minute expiry clock. Active workloads stay warm indefinitely; idle workloads expire in 5 minutes.
- **Cache breakeven threshold** — The reads-per-write ratio above which caching saves money. For a 10k-token system prompt, roughly 1.3 reads per 5-minute window. Below that, the write premium exceeds the read discount.
- **Keep-alive ping** — A lightweight request (max_tokens=1) fired every ~4 minutes to reset the TTL on a high-value cache. Requires a persistent process; useless in serverless/cron contexts.
- **Request batching** — Accumulating work into tight bursts so multiple requests share a single cache write. The classic fix for cron-paced workloads where each invocation would otherwise cold-start.
- **Cache hit rate** — `cache_read_input_tokens / (cache_read_input_tokens + cache_creation_input_tokens)`. The single metric to instrument; below 60% with large prefixes means caching is net-negative.
- **Byte-identical prefix** — The hard requirement for cache hits. Any character drift in the cached block invalidates the cache for that conversation.

## Related Articles

- [[effective-context-engineering]] — Attention budget and just-in-time retrieval; structural pairing with cache-aware prompt ordering.
- [[claude-api-pricing-breakdown-2026]] — The full pricing table for Haiku 4.5, Sonnet 4.6, and Opus 4.7 that the cache math sits on top of.
- [[claude-opus-4-7-release]] — Opus 4.7's new tokenizer pushes prompts up to 1.35× more tokens, compounding cache write cost for code-heavy prefixes.
- [[effective-harnesses-long-running-agents]] — Long-running harnesses with initializer + coding agent sessions naturally fragment into multi-request windows where batching survives.
- [[memory-for-ai-agents-context-engineering]] — Memory architectures determine how much static context sits in the cached prefix vs in dynamic retrieval.

## Relevance to AgentNexLiFy

The widget chat backend is the textbook keep-alive candidate: always-on FastAPI process, ~1,200 token system prompt, high-frequency tenant conversations, steady message cadence. Caching should be on, the system prompt block should carry `cache_control: {type: "ephemeral"}`, and the `chat_service.py` path must preserve byte-identical prefix ordering (any per-tenant system prompt interpolation goes in the user message, not the cached block). The cron-paced workloads are different: `scripts/daily/nightly-commit-review.sh`, `scripts/daily/kb-autopopulate.sh`, and `scripts/claude-hooks/*.sh` all run at intervals longer than 5 minutes and should either batch requests within a single run or skip caching entirely. The measurement imperative is concrete: instrument `response.usage.cache_creation_input_tokens` and `cache_read_input_tokens` in `backend/services/llm_runtime.py`, log hit rate per call site daily, and flag any call site below 60% hit rate as a candidate to disable caching. The ~$400-600/mo estimate in earlier caching analysis assumed 60-minute TTL; with 5-minute TTL it's closer to $150-250/mo savings if properly configured, and potentially negative savings if mis-configured.
