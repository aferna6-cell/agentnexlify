---
title: Prompt Caching — How We Cut Claude API Costs by 90% in Production
date: 2026-05-27
source_url: https://iron-mind.ai/blog/prompt-caching-claude-production
fetched_at: 2026-08-26
category: ai_llm
tags: [anthropic, prompt-caching, cache-control, ttl, cost-optimization, cache-hit-ratio, monitoring]
---

# Prompt Caching: How We Cut Claude API Costs by 90% in Production

*Author: Niro Knox (Iron Mind). Published 2026-05-17, updated 2026-05-27.*

## Economics

- Cached reads cost **~10%** of the normal input price.
- Cache writes cost **1.25×** input price (5-minute TTL) or **2×** (1-hour TTL).
- Minimum cacheable prefix: **1,024 tokens** on Sonnet/Opus, **2,048 tokens** on Haiku. Below the minimum the `cache_control` marker is **silently ignored** — no error, no cache.
- Up to **4 breakpoints** per request via `"cache_control": {"type": "ephemeral"}`.

Real result reported: per-turn input cost **$0.042 → $0.0048 (−88%)** after restructuring the prompt.

## The metric that matters

```
cache_hit_ratio = cache_read_input_tokens /
                  (cache_read_input_tokens + cache_creation_input_tokens + uncached_input_tokens)
```

- `< 70%` almost always means the prefix is structured wrong, not that traffic is too low.
- Alert at `< 75%`.
- Read `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` on every response and log them per call site.

## Four mistakes that kill cache hits

1. **Variable content above stable content** — a timestamp, user name, or request ID before the system prompt invalidates the whole prefix every call.
2. **Breakpoint inside a dynamic block** — the marker must sit at the end of the last stable segment.
3. **Prefix below minimum size** — marker ignored silently.
4. **5-minute TTL expiring on bursty traffic** — scheduled jobs that fire every 15 min pay a write every time.

## Recommended prompt structure

```
[1] identity / role            (stable)
[2] tool definitions           (stable)
[3] KB / tenant context        (stable per tenant)  ← breakpoint
[4] session context            (stable per session) ← breakpoint
[5] dynamic turn content       (never cached)
```

## Choosing TTL

- **5-minute** for continuous interactive traffic (chat) — hits refresh the TTL for free.
- **1-hour** for bursty or scheduled traffic. Example: an automation firing every 15 minutes pays four 1.25× writes per hour (= 5×) on the 5-min TTL vs one 2× write on the 1-hour TTL — a **60% saving**.

## When to skip caching

- Low volume: fewer than 3–4 hits per TTL window (writes cost more than they save).
- Fully variable prompts with no stable prefix.
- Tiny prompts under the minimum.

## Notes for AgentNexLiFy

- Widget chat: tenant KB + system prompt easily clears 1,024 tokens → breakpoint after KB context; 5-min TTL fine because conversations are bursty-but-continuous.
- Backend scheduled jobs (`automation/scheduled_jobs.py`, 15-min polling loops): use 1-hour TTL per the math above.
- Add `cache_read_input_tokens` / `cache_creation_input_tokens` to `llm_runtime.py` usage logging and compute hit ratio per call site; alert < 75%.
- Confirm nothing dynamic (tenant name, timestamps) is interpolated *above* the stable block in `build_system_prompt`-style helpers.
