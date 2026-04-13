---
title: "Claude Opus 4.6 — Agentic Coding, 1M Context, Adaptive Thinking"
category: ai-llm
tags: ["claude", "opus-4-6", "anthropic", "agentic-coding", "1m-context", "adaptive-thinking", "context-compaction"]
sources: ["raw/ai-llm/claude-opus-4-6.md"]
created: 2026-04-12
updated: 2026-04-12
summary: "Opus 4.6 (released Feb 5, 2026) ships a 1M-token context, adaptive thinking, four effort levels, 128k output, and context compaction at the same $5/$25-per-million pricing as Opus 4.5."
---

# Claude Opus 4.6 — Agentic Coding, 1M Context, Adaptive Thinking

Claude Opus 4.6 shipped on February 5, 2026 as Anthropic's new frontier model, keeping pricing identical to Opus 4.5 at $5 per million input tokens and $25 per million output tokens. The headline capability is a 1M token context window in beta — a first for the Opus class — with premium pricing above 200k tokens ($10/$37.50 per million in/out). Opus 4.6 leads the industry on Terminal-Bench 2.0 (agentic coding), Humanity's Last Exam (multidisciplinary reasoning), and BrowseComp (hard-to-find online information retrieval), and outperforms GPT-5.2 by roughly 144 Elo points on GDPval-AA, the economically-valuable-knowledge-work benchmark. For AgentNexLiFy's [[model-routing]] decisions, Opus 4.6's positioning is clear: it replaces Opus 4.5 at the same cost for planning, architecture review, and complex agentic coordination work, while everyday implementation stays on Sonnet 4.6 (see [[claude-sonnet-4-6-release]]).

Four structural API features shipped alongside the model and are the real product story for developers. Adaptive thinking lets the model decide when extended thinking is worth spending on, controlled by four effort levels — low, medium, high (default), max — replacing the prior binary on/off toggle. Context compaction (beta) automatically summarizes and replaces older context as conversations approach a configurable threshold, letting agentic loops run longer than the raw context window would normally allow. The 1M token context window holds entire large codebases; on the 8-needle 1M variant of MRCR v2 (needle-in-a-haystack retrieval), Opus 4.6 scores 76% vs. Sonnet 4.5's 18.5%, which is the specific metric that matters for long-horizon agent work where "context rot" historically caused silent quality degradation. Output tokens go up to 128k per response, letting the model complete large single-shot tasks like full codebase migrations without manual chunking.

The coding story is where Anthropic leaned hardest. Early-access partner quotes describe Opus 4.6 handling multi-million-line codebase migrations "like a senior engineer," one-shotting a fully functional physics engine, and closing 13 issues plus assigning 12 others autonomously across a ~50-person organization spanning six repositories in a single day. On cybersecurity investigations run end-to-end with up to 9 subagents and 100+ tool calls, Opus 4.6 won 38 of 40 blind comparisons against Claude 4.5 models. Devin Review reports increased bug-catch rates. BigLaw Bench hit 90.2% with 40% perfect scores — a legal-reasoning benchmark most models fail on. These are not marketing claims about "feels better"; they are structured evaluations with published numbers, which is the appropriate bar before committing to a model in production.

Claude Code shipped agent teams as a research preview in the same release: multiple subagents running in parallel, coordinating autonomously, best suited for read-heavy tasks like codebase reviews. The human operator can take over any subagent with Shift+Up/Down or tmux. This pairs directly with AgentNexLiFy's [[llm-wiki-karpathy-pattern]] compound-engineering workflow, where the Brainstormer → Planner → Executor → Reviewer → Vertical Checker pipeline has historically been driven sequentially from the main session. Agent teams let those phases run in parallel where dependencies allow, with the orchestrator model picking when to converge.

Safety profile improved on every dimension measured. Opus 4.6 shows the lowest over-refusal rate of any recent Claude model (benign queries correctly answered) while also scoring lowest on misaligned behaviors (deception, sycophancy, delusion-encouragement, misuse cooperation). Anthropic ran the most comprehensive safety evaluation suite of any Claude release to date, including six new cybersecurity probes to track potential misuse given the model's enhanced offensive-security capabilities, and began using interpretability methods to trace model behavior to internal circuits. The Responsible Scaling Policy framework described in [[anthropic-mission-and-latest-releases]] gates these capabilities; the cybersecurity probes are the kind of real-time safeguard layer that will likely expand as offensive capability continues to outpace defensive deployment.

Practical cost notes: Opus is 5x Sonnet and 15x Haiku per token, so the Opus-plans / Sonnet-executes / Haiku-cleans pattern in [[model-routing]] remains the correct routing under Opus 4.6. Adaptive thinking and effort controls mean Opus calls can now be tuned per-task rather than paying maximum-reasoning cost on every invocation. Context compaction plus 1M context unlock workflows that were previously impossible (whole-repo refactors, multi-document legal review, end-to-end research agents), but the premium tier above 200k tokens is 2x input/1.5x output — enough to make the compaction-versus-1M-window tradeoff a deliberate economic choice, not a free default.

## Key Concepts

- **Adaptive Thinking** — Opus 4.6 capability where the model itself decides when extended reasoning is worth spending on, controlled by four effort levels (low/medium/high/max). Replaces the earlier binary extended-thinking toggle.
- **Context Compaction (beta)** — API feature that automatically summarizes older context as a conversation approaches a configurable threshold, enabling longer agentic loops than the raw context window allows.
- **1M Token Context** — Opus 4.6's beta context window on the Claude Developer Platform; premium pricing ($10/$37.50 per million in/out) applies above 200k tokens.
- **MRCR v2 (Multi-Round Context Retrieval)** — Needle-in-a-haystack retrieval benchmark across long contexts; Opus 4.6 scores 76% on the 8-needle 1M variant vs. Sonnet 4.5's 18.5%.
- **GDPval-AA** — Artificial Analysis evaluation of economically-valuable knowledge work (finance, legal, analysis); Opus 4.6 leads GPT-5.2 by ~144 Elo points.
- **Agent Teams** — Claude Code research preview where multiple subagents run in parallel and coordinate autonomously; human operator can take over any subagent via Shift+Up/Down or tmux.

## Related Articles

- [[claude-sonnet-4-6-release]] — Sonnet 4.6 release details; pairs with Opus 4.6 under the advisor-executor pattern for cost-optimized agentic work.
- [[anthropic-mission-and-latest-releases]] — Broader context on Anthropic's release cadence and the Responsible Scaling Policy that gates agentic capability deployment.
- [[llm-wiki-karpathy-pattern]] — The compound-engineering pattern that Agent Teams accelerate by running Brainstormer/Planner/Executor/Reviewer/Checker phases in parallel.

## Relevance to AgentNexLiFy

Opus 4.6 changes three things for the platform. First, the advisor-executor pattern documented in `.claude/rules/model-routing.md` gets cheaper and smarter — Opus 4.6 advisor briefs now have 1M context and adaptive thinking, so reading 10+ files for a plan brief is feasible without chunking, and the brief itself burns less budget on trivial tasks. Second, context compaction unlocks long-running managed-agent workflows (lead qualification across multi-hour conversations, multi-session follow-up) that previously hit the context window mid-conversation; the backend `managed_agents_registry.py` path can now accept much longer session histories before summarizing. Third, Anthropic's Claude Code agent teams validate the five-agent compound pipeline architecture the project already uses — the industry is converging on the same pattern, which lowers the risk that the investment becomes orphaned. Near-term action: migrate any code paths still pinned to `claude-opus-4-5` to `claude-opus-4-6` (identical pricing) and audit managed-agents session history truncation logic to take advantage of context compaction instead of hard-truncating at the old 200k threshold.
