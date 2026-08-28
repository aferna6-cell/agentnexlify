---
title: GPT-5.5 Review 2026 — Benchmarks vs Claude Opus 4.7, Pricing, Context
date: 2026-05-10
source_url: https://www.buildfastwithai.com/blogs/gpt-5-5-review-benchmarks-2026
fetched_at: 2026-08-26
category: frontier_ai
tags: [openai, gpt-5-5, claude-opus-4-7, benchmarks, swe-bench, terminal-bench, arc-agi, pricing, long-context]
---

# GPT-5.5 Review 2026

*Build Fast with AI. May 10, 2026.*

## Release facts

- Codename "Spud". Launched **April 23, 2026**; became ChatGPT default **May 5, 2026**.
- First full retrain since GPT-4.5; natively omnimodal.
- Co-designed with NVIDIA GB200 / GB300 hardware.
- Context: **1M tokens** via API, **400K** in Codex. Knowledge cutoff **Dec 2025**.
- Not available on ChatGPT free tier.
- Hallucination rate reported **−52.5%** vs GPT-5.4.

## Pricing

**$5 input / $30 output per MTok** — 2× GPT-5.4 list price. OpenAI claims ~40% fewer tokens per task, so effective cost increase is ~20%.

## Benchmarks vs Claude Opus 4.7

| Benchmark | GPT-5.5 | Claude Opus 4.7 | Leader |
|---|---|---|---|
| Terminal-Bench 2.0 | 82.7 | 69.4 | GPT-5.5 |
| ARC-AGI-2 | 85.0 | 75.8 | GPT-5.5 |
| MRCR v2 (long-context recall) | 74.0 | 32.2 | GPT-5.5 |
| Long-context 128–256K | 87.5 | 59.2 | GPT-5.5 |
| SWE-Bench Pro | 58.6 | 64.3 | Claude |
| HLE (no tools) | 41.4 | 46.9 | Claude |
| MCP Atlas | 75.3 | 79.1 | Claude |
| GPQA | 93.6 | 94.2 | Claude |

Pattern: GPT-5.5 wins on terminal/agentic-shell tasks and very long context; Claude wins on real-repo software engineering (SWE-Bench Pro), tool-use protocol tasks (MCP Atlas), and science QA.

## Notes for AgentNexLiFy

- Snapshot is pre-Opus 4.8 / Fable 5 (June 2026) — treat as historical. Useful mainly as the long-context data point: Claude 4.7-era models degraded sharply past 128K; keep tenant KB context well under that and rely on retrieval.
- No reason to add an OpenAI provider for widget chat — SWE/MCP/GPQA parity and our Anthropic-native Managed Agents stack outweigh the terminal-bench gap.
