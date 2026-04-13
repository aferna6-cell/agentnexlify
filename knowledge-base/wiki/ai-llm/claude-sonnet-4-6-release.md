---
title: "Claude Sonnet 4.6 — Near-Opus Coding at Sonnet Pricing"
category: ai-llm
tags: ["claude", "sonnet-4-6", "anthropic", "computer-use", "osworld", "1m-context", "coding"]
sources: ["raw/ai-llm/claude-sonnet-4-6.md"]
created: 2026-04-12
updated: 2026-04-12
summary: "Sonnet 4.6 (Feb 17, 2026) holds $3/$15 per million pricing while preferring-over-Opus-4.5 59% of the time in Claude Code, adding 1M context, 94% on insurance computer-use benchmarks, and matching Opus 4.6 on OfficeQA."
---

# Claude Sonnet 4.6 — Near-Opus Coding at Sonnet Pricing

Claude Sonnet 4.6 shipped on February 17, 2026 at identical Sonnet 4.5 pricing ($3 per million input tokens, $15 output) and immediately became the default model on claude.ai Free and Pro plans and Claude Cowork. The release is a broad upgrade — coding, computer use, long-context reasoning, agent planning, knowledge work, and design — and it also ships a 1M token context window in beta, matching what Opus 4.6 (see [[claude-opus-4-6-release]]) got two weeks earlier. The most important user-visible number: in early Claude Code testing, users preferred Sonnet 4.6 over Sonnet 4.5 roughly 70% of the time, and preferred it over the November 2025 frontier model Opus 4.5 59% of the time. That reverses the normal price-versus-intelligence tradeoff — for most AgentNexLiFy coding work, Sonnet 4.6 is now both cheaper and preferred.

Computer use is the capability that jumped most. On OSWorld-Verified — hundreds of tasks across real software (Chrome, LibreOffice, VS Code) running on a simulated computer, with the model clicking virtual mice and typing virtual keys — Sonnet 4.6 continues the steady 16-month improvement arc from the first general-purpose computer-using model Anthropic shipped in October 2024. Early users report human-level capability on complex spreadsheet navigation and multi-step web form workflows that span multiple browser tabs. On a customer insurance benchmark (submission intake, first notice of loss), Sonnet 4.6 hit 94% — described by the customer as mission-critical-grade accuracy. Prompt-injection resistance, the critical safety property for agents that browse arbitrary sites, improved to Opus 4.6-parity from a worse baseline on Sonnet 4.5.

The cost-quality story is built on specific customer evals. Box reports 15-percentage-point gains on heavy-reasoning document Q&A over Sonnet 4.5. Rakuten AI describes Sonnet 4.6 as producing the best iOS code they've tested — better spec compliance, better architecture, reaching for modern tooling unprompted, all in one shot. A financial services customer reports a significant jump in answer-match rate on their internal benchmark, with better recall on customer-specific workflows. OfficeQA (reading enterprise documents — charts, PDFs, tables — and reasoning from them) shows Sonnet 4.6 matching Opus 4.6, which is the specific result that matters for Claude in Excel workflows and by extension for any AgentNexLiFy analytics pipeline that reads tenant-uploaded documents.

Users independently flagged behavioral improvements that matter for long-session work: less overengineering, less "laziness" (giving up or hedging), better instruction following, fewer false claims of success, fewer hallucinations, and more consistent follow-through on multi-step tasks. On Vending-Bench Arena — a simulated-business-running evaluation that tests long-horizon planning under competition — Sonnet 4.6 developed a novel strategy of heavy capacity investment in early months followed by a sharp pivot to profitability in the final stretch, finishing well ahead. The pattern matters because it's evidence of genuine long-range planning rather than greedy per-turn optimization, which is the failure mode most prior models exhibited on multi-month simulated tasks.

API features that shipped with the model: adaptive thinking (same feature as Opus 4.6 — model decides when to reason extended), extended thinking still available for explicit control, context compaction (beta) for long-running agentic tasks. Code execution, memory, programmatic tool calling, tool search, and tool-use examples are all now GA. Web search and fetch tools automatically write and execute code to filter search results, keeping only relevant content in context — a quality-and-token-efficiency improvement that matters at scale. Claude in Excel now supports MCP connectors (S&P Global, LSEG, Daloopa, PitchBook, Moody's, FactSet), meaning the same MCP connections set up in claude.ai flow through to the Excel add-in.

Anthropic's guidance on Sonnet 4.6 vs. Opus 4.6 selection: Opus remains the stronger choice for tasks demanding the deepest reasoning — codebase refactoring, coordinating multiple agents in a workflow, and problems where getting it exactly right is paramount. Sonnet 4.6 is the right default for everything else, including the economically-valuable office tasks that previously required reaching for an Opus-class model. For AgentNexLiFy the rule in [[model-routing]] holds: Opus plans, Sonnet executes, Haiku cleans — but Sonnet 4.6 takes on more of the planning work that Opus 4.5 was handling six months ago, because the 59% preference-over-Opus-4.5 result means the capability gap has closed for most real tasks.

## Key Concepts

- **OSWorld-Verified** — The updated (July 2025) benchmark for AI computer use, testing hundreds of tasks across real software on a simulated OS. The standard measure of how well a model can click, type, and navigate like a human.
- **Prompt Injection Resistance** — Model's ability to reject hidden malicious instructions embedded in websites during computer-use sessions. Sonnet 4.6 improved to Opus 4.6-parity from Sonnet 4.5.
- **Vending-Bench Arena** — Long-horizon planning evaluation where models run a simulated business over months and compete head-to-head on profitability. Tests genuine multi-step planning, not greedy per-turn optimization.
- **OfficeQA** — Benchmark for reading enterprise documents (charts, PDFs, tables) and reasoning from extracted facts. Sonnet 4.6 matches Opus 4.6 performance here.
- **Adaptive Thinking** — Model-directed decision about when to use extended reasoning, same feature as introduced on Opus 4.6; see [[claude-opus-4-6-release]].
- **1M Token Context (beta)** — Sonnet 4.6's expanded context window, enough to hold entire codebases, lengthy contracts, or dozens of research papers in a single request.

## Related Articles

- [[claude-opus-4-6-release]] — Opus 4.6 release details; sets the Opus-vs-Sonnet selection guidance that Sonnet 4.6 changes by narrowing the capability gap.
- [[anthropic-mission-and-latest-releases]] — Broader Anthropic release cadence and safety framework.
- [[llm-wiki-karpathy-pattern]] — Compound-engineering pattern; Sonnet 4.6 now handles more of the planning work previously routed to Opus.

## Relevance to AgentNexLiFy

Direct cost and quality upside with no migration risk: swap every `claude-sonnet-4-5` reference in `backend/` to `claude-sonnet-4-6` — pricing is identical, preference over 4.5 is 70% in Claude Code evals, and customer reports across coding, finance, and document-reasoning verticals are unambiguously positive. The bigger strategic move is revisiting the advisor-executor split in `.claude/rules/model-routing.md`: Sonnet 4.6 can now execute tasks that previously required Opus advisor briefs, which is the cheapest quality improvement available. For managed-agents workflows (`backend/services/advisor_executor.py`), the Lead Qualifier and similar agents should move their execution model to Sonnet 4.6 immediately and measure whether the advisor step can be dropped for simpler flows. Computer-use improvements open a new product surface that the platform hasn't used yet — a Sonnet 4.6 agent that fills out competitor intake forms, scrapes GoHighLevel pricing pages, or automates tenant onboarding flows is now within capability, though prompt-injection mitigations from the Anthropic API docs are mandatory before pointing any such agent at arbitrary websites.
