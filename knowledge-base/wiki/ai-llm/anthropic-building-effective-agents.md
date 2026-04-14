---
title: "Building Effective AI Agents — Anthropic's Pattern Catalog"
category: ai-llm
tags: [agent-patterns, workflows, orchestration, tool-use, anthropic]
sources: ["raw/ai-llm/anthropic-building-effective-agents.md"]
created: 2026-04-14
updated: 2026-04-14
summary: "Anthropic's canonical guide to agentic systems: five composable workflow patterns (chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) plus autonomous agents — simplicity wins over frameworks."
---

# Building Effective AI Agents — Anthropic's Pattern Catalog

Anthropic's most-referenced engineering post distills lessons from working with dozens of production agent teams into a clear taxonomy: workflows (predefined code paths orchestrating LLMs) versus agents (LLMs dynamically directing their own processes). The consistent finding is that the most successful implementations use simple, composable patterns rather than complex frameworks. This directly challenges the instinct to reach for agent SDKs and multi-layer abstractions. For AgentNexLiFy, which runs a compound engineering pipeline with five sequential agents, the post validates the pattern while cautioning against premature complexity — start with optimized single LLM calls and only add agentic orchestration when simpler solutions demonstrably fall short.

The foundational building block is the augmented LLM: a model enhanced with retrieval, tools, and memory. Current models can actively generate search queries, select tools, and determine what information to retain. The Model Context Protocol (MCP) standardizes this augmentation layer, and AgentNexLiFy already uses MCP servers for Supabase, Railway, and Playwright. Every agentic pattern in the catalog assumes this augmented base, making tool quality and documentation as important as prompt quality.

Five workflow patterns cover the structured end of the spectrum. **Prompt chaining** decomposes tasks into sequential steps with programmatic gates between them — ideal when subtasks are fixed and each step is simple enough for high accuracy. **Routing** classifies inputs and directs them to specialized handlers, matching AgentNexLiFy's model routing pattern where Haiku handles simple queries and [[claude-sonnet-4-6-capabilities]] handles complex ones. **Parallelization** runs subtasks simultaneously, either as sectioning (independent subtasks) or voting (same task, multiple perspectives for confidence). **Orchestrator-workers** uses a central LLM to dynamically decompose tasks and delegate to workers — the pattern behind coding agents like Claude Code and AgentNexLiFy's compound engineering pipeline. **Evaluator-optimizer** creates a generate-then-critique loop, analogous to the GAN harness pattern already used in the project.

The autonomous agent pattern sits at the highest complexity level. Agents plan and operate independently after receiving a task, using tool results as ground truth to assess progress. The post emphasizes that agent implementation is often straightforward — typically just an LLM calling tools in a loop based on environmental feedback. The complexity comes from the cognitive demands on the model, not the code. Two production domains stand out: customer support (natural conversation flow + tool integration + measurable success criteria) and coding agents (verifiable solutions via automated tests + iterative feedback loops). AgentNexLiFy's chat widget operates squarely in the customer support domain.

The agent-computer interface (ACI) concept is the post's most actionable insight. Just as HCI research optimizes human-computer interactions, ACI requires equal investment in optimizing how agents interact with tools. Practical recommendations include: use absolute file paths instead of relative ones (Claude makes mistakes after changing directories), choose output formats close to what models have seen in training data (markdown over JSON for code), avoid formats with "overhead" like maintaining accurate line counts in diffs, and test tools extensively in the workbench to find and fix failure patterns. The Anthropic team reports spending more time optimizing tools than overall prompts during their SWE-bench agent development.

The framework guidance is nuanced. Frameworks like the Claude Agent SDK, Rivet, and Vellum make it easy to get started, but they create abstraction layers that obscure underlying prompts and responses, making debugging harder. The recommendation is to start with direct LLM API calls — many patterns take only a few lines of code — and only adopt frameworks when the benefits clearly outweigh the debugging cost. Incorrect assumptions about what's under the hood are flagged as the most common source of customer errors with frameworks.

Three core principles for agent design emerge: maintain simplicity (don't add complexity unless it demonstrably improves outcomes), prioritize transparency (explicitly show planning steps), and carefully craft the ACI through thorough tool documentation and testing. These align with the [[llm-wiki-karpathy-pattern]] philosophy of compounding quality through disciplined, incremental refinement rather than architectural ambition.

## Key Concepts

- **Agentic systems** — Anthropic's umbrella term covering both workflows (predefined orchestration) and agents (dynamic, model-directed orchestration). The distinction matters because workflows offer predictability while agents offer flexibility.
- **Agent-Computer Interface (ACI)** — The tool definitions, parameter schemas, documentation, and error handling that shape how an agent interacts with external systems. Requires the same investment as HCI design.
- **Prompt chaining** — Sequential LLM calls where each processes the output of the previous one, with programmatic gates for validation between steps. Trades latency for accuracy.
- **Orchestrator-workers** — A central LLM dynamically decomposes tasks and delegates to worker LLMs. Key difference from parallelization: subtasks aren't predefined but determined by the orchestrator based on input.
- **Evaluator-optimizer** — A generate-then-critique loop where one LLM produces output and another evaluates it, iterating until quality thresholds are met. Requires clear evaluation criteria.

## Related Articles

- [[claude-sonnet-4-6-capabilities]] — The default execution model for AgentNexLiFy's agent workflows; its cost-efficiency makes multi-turn agentic loops economically viable.
- [[claude-opus-4-6-capabilities]] — Used as the planning/advisory brain in orchestrator-worker patterns where depth of reasoning justifies the cost.
- [[llm-wiki-karpathy-pattern]] — Shares the simplicity-first philosophy: compound quality through disciplined patterns, not architectural ambition.
- [[competitive-landscape-march-2026]] — Competitor approaches to AI agents in customer support, the primary production domain validated by this post.

## Relevance to AgentNexLiFy

AgentNexLiFy's compound engineering pipeline (brainstorm → plan → execute → review → vertical check) maps directly to the orchestrator-workers pattern with an evaluator-optimizer feedback loop. The post validates this architecture but warns against complexity for its own sake. The customer support domain is called out as the #1 production use case for agents — exactly where AgentNexLiFy's chat widget operates. The ACI recommendations should be applied to the lead qualifier's tool definitions: clear parameter documentation, realistic examples, and absolute paths/IDs instead of ambiguous references. The routing pattern validates the model routing strategy (Haiku for simple, Sonnet for complex, Opus for planning) as a proven production approach.
