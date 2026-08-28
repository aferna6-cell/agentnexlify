---
title: Prompt Caching for Claude — Cut API Bill 60% in Production
date: 2026-04-17
source_url: https://www.aimagicx.com/blog/prompt-caching-claude-api-cost-optimization-2026
fetched_at: 2026-08-25
category: ai_llm
tags: [anthropic, prompt-caching, cost-optimization, rag, ttl, cache-hit-rate]
---

# Prompt Caching for Claude: Cut Your API Bill 60% in Production

**Published:** April 17, 2026 · AI Magicx Team

## How Prompt Caching Works

Designate prompt portions as cacheable. The first request with that prefix pays full price to establish the cache. Subsequent calls within the TTL window use cache-read pricing — roughly 10% of standard input costs.

| TTL | Cache Write Cost | Cache Read Cost | Use Case |
|-----|------------------|-----------------|----------|
| 5 minutes | 1.25x base input | 0.1x base input | Short conversations, rapid iteration |
| 1 hour | 2x base input | 0.1x base input | Long sessions, system prompts, RAG contexts |

"The cache is keyed on the exact bytes of the cached portion plus the model version. Any change — a single whitespace edit, a timestamp, a user name — invalidates the cache."

Break-even: aim for 3+ reads within the 5-minute TTL, or 5+ reads for the 1-hour option.

## Five Patterns That Work

### 1. Large System Prompts
A 4,000-token system prompt costs $0.012/request uncached (Sonnet rates); cached reads drop to $0.0012. At 10,000 daily requests, ~$108/day saved on Sonnet; Opus ~5x more.

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": LARGE_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral", "ttl": "1h"}
        }
    ],
    messages=[{"role": "user", "content": user_query}]
)
```

### 2. RAG Context Caching
Retrieved context spans 5,000–30,000 tokens/request and often stays fixed between turns.

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"<context>{retrieved_documents}</context>",
                "cache_control": {"type": "ephemeral", "ttl": "1h"}
            },
            {"type": "text", "text": user_query}
        ]
    }
]
```

10-turn conversation with 30,000-token context: uncached 300,000 input tokens × $3/M = $0.90; cached (1 write + 9 reads) = 57,000 effective = $0.175 (~5x reduction).

### 3. Conversation History Caching

```python
cached_messages = conversation_history[:-1]
cached_messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral", "ttl": "5m"}
messages = cached_messages + [current_user_turn]
```

Long conversational agents typically cut input costs roughly in half.

### 4. Tool Definitions Caching
Agents with many tools consume 3,000–8,000 tokens on schemas per request. Claude automatically caches tool definitions when a cache_control block appears in the system prompt — 40–70% cost reductions for agent workloads.

### 5. Few-Shot Examples Caching
Large few-shot blocks rarely change, so they cache well.

```python
system=[
    {"type": "text", "text": short_instructions},
    {
        "type": "text",
        "text": large_few_shot_block,
        "cache_control": {"type": "ephemeral", "ttl": "1h"}
    }
]
```

## Production Numbers

- **Customer Support Chatbot (Sonnet 4.6)** — 50,000 req/day; system prompt 3,200 tok + KB context 15,000 tok + user 600 tok. Before $8,820/mo → After $3,105/mo (**65% saved**)
- **Code Review Agent (Opus 4.6)** — 800 PRs/mo; 1,800 + 14,000 + 5,000 + 7,000 tok. Before $2,190/mo → After $642/mo (**71%**)
- **Research Assistant (Sonnet 4.6)** — 10,000 sessions/mo, 4.5-turn avg, history to 40,000 tok. Before $4,140/mo → After $1,650/mo (**60%**)

Average across all three: **65% savings**, 2–4 hours implementation per workload.

## Anti-Patterns

1. **Timestamps in cached content** — "Current time: 2026-04-17T14:32:15Z" invalidates on every request. Move outside the cached prefix or truncate to day precision.
2. **User-specific content in prefix** — "You are helping {user.name} at {user.company}" causes a cache miss per user. Move to the user message or use per-user caches with extended TTL.
3. **Frequent whitespace changes** — inconsistent prompt construction yields ~80% needless misses. Normalize aggressively.
4. **Model version migrations** — new model releases invalidate caches. Plan cache warmup alongside upgrades.
5. **Caching short prefixes** — minimum cacheable prefix is 1,024 tokens (Sonnet) / 2,048 (Opus). Verify `cache_creation_input_tokens`; zero means caching failed.

## Measuring Cache Effectiveness

```python
usage = response.usage
print(f"Input tokens: {usage.input_tokens}")
print(f"Cache read tokens: {usage.cache_read_input_tokens}")
print(f"Cache creation tokens: {usage.cache_creation_input_tokens}")
print(f"Output tokens: {usage.output_tokens}")
```

Hit rate = `cache_read_input_tokens / (cache_read_input_tokens + input_tokens)`. Below 60% on production workloads signals optimization headroom.

## 5-Minute vs 1-Hour TTL

- User-interactive chat → 5-minute TTL, refreshed per message
- Long-lived system prompts → 1-hour TTL
- RAG contexts in extended sessions → 1-hour TTL
- High-frequency agent loops → 5-minute TTL
- Rarely-changing tool definitions → 1-hour TTL

Most production workloads combine 1-hour TTL on static prefixes with 5-minute TTL on conversation history.

## The Bigger Opportunity

Two compounding levers beyond caching: **model routing** (simple tasks to Haiku, complex to Opus — same workload can cost 30x less) and **constrained output budgets**. Combined, unoptimized workloads typically drop to 20–30% of baseline.

Start this week: enable caching on your largest system prompt, add cache hit rate metrics to dashboards, audit prompts for timestamp/user-context/whitespace anti-patterns. Typically recovers 30–50% of API costs.
