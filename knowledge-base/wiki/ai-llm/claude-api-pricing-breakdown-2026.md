---
title: "Claude API Pricing Breakdown — Haiku 4.5, Sonnet 4.6, Opus 4.7 in 2026"
category: ai-llm
tags: [claude-api, pricing, anthropic, haiku-4-5, sonnet-4-6, opus-4-7, tokenizer, cost-optimization]
sources: ["raw/ai-llm/ofox-ai-blog-claude-api-pricing-complete-breakdown-2026.md"]
created: 2026-04-23
updated: 2026-04-23
summary: "Claude has six active API models in 2026 at $1/$5 (Haiku 4.5) through $5/$25 (Opus 4.7) per million tokens; Opus 4.7's new tokenizer raises effective code-prompt cost 5-35% despite identical list price, and prompt caching is the dominant unused cost lever."
---

# Claude API Pricing Breakdown — Haiku 4.5, Sonnet 4.6, Opus 4.7 in 2026

Anthropic's Claude API lineup in 2026 spans six active models across three tiers, with list prices that look identical within each tier but diverge meaningfully once tokenizer changes and caching are factored in. Haiku 4.5 sits at $1/$5 per million input/output tokens with a 200K context window. Sonnet 4.5 and 4.6 both sit at $3/$15 — identical on paper; pick 4.6 if starting fresh because it scores 79.6% on SWE-bench Verified against 4.5's older benchmark. Opus 4.5, 4.6, and 4.7 all list at $5/$25. The surface reading is that upgrading from Opus 4.6 to 4.7 is free. The real reading is that Opus 4.7's new tokenizer maps the same content to 1.0-1.35x more tokens, which makes the same workload cost 5-35% more in practice — a fact Anthropic's own migration guide publishes but many teams miss.

| Model | Model ID | Input / 1M | Output / 1M | Context |
|---|---|---|---|---|
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | $1.00 | $5.00 | 200K |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | $3.00 | $15.00 | 200K |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | $3.00 | $15.00 | 200K |
| Claude Opus 4.5 | `claude-opus-4-5` | $5.00 | $25.00 | 200K |
| Claude Opus 4.6 | `claude-opus-4-6` | $5.00 | $25.00 | 200K |
| Claude Opus 4.7 | `claude-opus-4-7` | $5.00 | $25.00 | 200K |

The tokenizer asymmetry matters most for code-heavy pipelines. Natural language prose maps 1.0-1.05x on Opus 4.7 vs 4.6 — negligible. Mixed code and text maps 1.1-1.2x — a real 10-20% cost creep. Dense Python or TypeScript maps 1.2-1.35x — 20-35% more. A code review pipeline spending $2,000/mo on Opus 4.6 should budget $2,200-2,700/mo on 4.7 for the same work, even though the list price never moved. Haiku and Sonnet are stable across generations, so the tokenizer surprise is strictly an Opus-4.7-upgrade problem. This caveat does not negate the upgrade — 4.7 is genuinely ahead on CursorBench (70% vs 58%) and Rakuten-SWE-Bench (3x production task resolution) per [[claude-opus-4-7-release]] — but "same price" is technically accurate and practically misleading.

Prompt caching is the dominant unused cost lever across all three tiers. Cache writes cost 1.25× base input; cache reads cost 0.10× base input. For Sonnet 4.6 at $3.00/M input, that's $3.75/M cache-write and $0.30/M cache-read. A 10,000-token system prompt sent across 1,000 requests per day goes from $30/day uncached to ~$3.04/day cached — roughly 90% savings on the cached prefix. The 5-minute TTL introduced in early 2026 (see [[claude-prompt-caching-5min-ttl-2026]]) constrains which workloads benefit, but for chat backends and high-frequency APIs the savings remain dramatic. Minimum cacheable block is 2,048 tokens for Sonnet 4.6 and 4,096 tokens for Opus and Haiku.

The model selection decision for most production workloads flattens to a simple heuristic. Haiku 4.5 handles classification, routing, simple summarization, and anything where thousands of calls per hour dominate the bill. Sonnet 4.6 is the right default for most production tasks — code generation, code review (79.6% SWE-bench), customer-facing output where quality matters but Opus is overkill. Opus 4.7 is reserved for complex multi-file refactoring, long autonomous agent runs, vision-heavy workflows (98.5% accuracy on 3.75MP images per [[vision-3x]] rules), and tasks where Sonnet has been benchmarked and is demonstrably hitting a ceiling. The honest stance is to start with Sonnet 4.6, measure, and only escalate to Opus when the quality gap shows up in production metrics. The 8-point SWE-bench gap between Sonnet 4.6 and Opus 4.7 is real but most production tasks never exercise the tail where it appears.

Rough token-count benchmarks anchor monthly-bill estimation. Short Q&A runs 200-500 input, 100-300 output. Single-file code review runs 2,000-5,000 input, 500-1,500 output. Document summarization runs 5,000-20,000 input, 500-2,000 output. A per-step agent loop runs 3,000-10,000 input, 500-2,000 output. A code review pipeline processing 500 files per day on Sonnet 4.6 lands at ~$12.75/day, ~$383/month before caching — reducible by 20-30% with correctly configured prompt caching on the system prompt block.

The aggregator option (ofox.ai, OpenRouter, etc.) collapses Claude, OpenAI, Gemini, and the rest behind a single OpenAI-compatible endpoint. One API key, one client, switch models by changing the `model` parameter. This matters for A/B testing and model-routing logic more than it matters for cost (aggregators typically pass list price through with a small markup). For AgentNexLiFy, direct Anthropic API access remains preferred to retain full access to Opus 4.7's `output_config.effort=xhigh`, task budgets, and adaptive thinking — features not fully exposed on all aggregator endpoints.

## Key Concepts

- **Tokenizer drift** — A model-family-specific change that alters how text is counted into tokens. Opus 4.7 ships a new tokenizer that expands code-heavy prompts 5-35% versus Opus 4.6 despite identical list price. Haiku and Sonnet are stable across generations.
- **Cache write premium** — The 25% markup on the first cached request (base_input × 1.25). Paid once per cache lifecycle. Below a breakeven read count, it dominates and makes caching net-negative.
- **Cache read discount** — The 90% reduction on subsequent cached requests (base_input × 0.10). What makes caching lucrative when the reads-per-write ratio is high.
- **Cacheable block minimum** — Sonnet 4.6 requires ≥2,048 tokens in a cached block; Opus (4.5/4.6/4.7) and Haiku 4.5 require ≥4,096. Prefixes below the threshold are not cached even with `cache_control` markers.
- **Breakeven reads-per-write** — The ratio above which caching saves money. Workload-dependent; roughly 1.3 for typical system prompts. Measuring via `response.usage.cache_read_input_tokens` is the only reliable way to confirm.
- **Aggregator endpoint** — An OpenAI-compatible proxy (ofox.ai, OpenRouter) that exposes multiple vendor models behind one API key. Useful for A/B testing; typically does not unlock vendor-specific features like Opus 4.7's `output_config.effort`.
- **xhigh effort** — Opus 4.7's extended thinking tier, exposed via `output_config.effort="xhigh"` on native Anthropic endpoints. Uses up to 100K thinking tokens; not universally available on aggregators.

## Related Articles

- [[claude-opus-4-7-release]] — Full feature matrix for Opus 4.7 including the new tokenizer, self-verification, task budgets, and xhigh effort.
- [[claude-prompt-caching-5min-ttl-2026]] — The 5-minute TTL change and the architecture patterns that preserve caching economics.
- [[claude-sonnet-4-6-capabilities]] — Why Sonnet 4.6 is the default production model and where it sits relative to Opus on benchmarks.
- [[claude-opus-4-6-capabilities]] — Previous-generation Opus; still relevant as the tokenizer baseline for 4.7 cost comparisons.
- [[effective-context-engineering]] — Attention budget and just-in-time retrieval reduce input token count independent of caching.

## Relevance to AgentNexLiFy

Three concrete decisions fall out of this pricing structure for AgentNexLiFy. First, the widget chat backend should stay on Sonnet 4.6 as the default model — the 79.6% SWE-bench score is more than enough for tenant chat qualification, and the 3x input / 3x output gap against Haiku 4.5 ($1/$5) creates room for Haiku routing on simple classification calls (intent detection, FAQ lookup) that don't need full reasoning. Second, the Opus 4.7 tokenizer drift means any call site using Opus in `backend/services/advisor_executor.py` or the nightly commit review needs its actual billed token cost re-measured, not estimated from prior Opus 4.6 runs — the 20-35% creep on code-heavy prompts will surprise a monthly budget built on 4.6 numbers. Third, prompt caching should be instrumented and verified on the widget system prompt block immediately if not already; the 90% read discount on a ~1,200-token prompt sent thousands of times per day is the single largest cost lever we have, and the 5-minute TTL is survivable for active chat sessions (see [[claude-prompt-caching-5min-ttl-2026]]). Cron-paced workloads (nightly review, KB compile) need explicit breakeven math before enabling caching — below 1.3 reads per invocation they lose money on the write premium.
