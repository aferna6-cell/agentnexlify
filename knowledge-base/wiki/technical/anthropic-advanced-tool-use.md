---
title: "Advanced Tool Use — Search, Programmatic Calling, and Examples"
category: technical
tags: [tool-use, tool-search, programmatic-calling, tool-examples, claude-api]
sources: ["raw/technical/anthropic-advanced-tool-use.md"]
created: 2026-04-14
updated: 2026-04-14
summary: "Three Claude API features — Tool Search Tool (85% token reduction), Programmatic Tool Calling (37% token savings via code orchestration), and Tool Use Examples (72%→90% accuracy) — that transform tool use from function calling into intelligent orchestration."
---

# Advanced Tool Use — Search, Programmatic Calling, and Examples

Anthropic released three beta features in November 2025 that address the fundamental bottlenecks in scaling tool use: context bloat from tool definitions, inference overhead from sequential tool calls, and parameter errors from ambiguous schemas. Together, they enable agents to work with hundreds of tools while keeping context lean, execution efficient, and invocations accurate. For AgentNexLiFy, which connects Claude to Supabase, Stripe, Resend, Twilio, and multiple MCP servers, these features directly address the token cost and accuracy challenges in the lead qualifier and chat widget agents.

The **Tool Search Tool** solves context bloat from loading all tool definitions upfront. A typical five-server MCP setup (GitHub, Slack, Sentry, Grafana, Splunk) consumes ~55K tokens before any conversation starts. Anthropic observed setups consuming 134K tokens in tool definitions alone. The solution marks tools with `defer_loading: true`, keeping them discoverable but not loaded into context. Claude sees only the Tool Search Tool itself (~500 tokens) plus a few critical always-loaded tools. When Claude needs specific capabilities, it searches by keyword, and only matching tools are expanded into full definitions. Internal testing showed Opus 4 accuracy jumping from 49% to 74% and Opus 4.5 from 79.5% to 88.1% on MCP evaluations — the accuracy improvement comes from reduced noise, not just token savings. The feature preserves prompt caching because deferred tools are excluded from the initial prompt entirely, as documented in [[pgvector-postgres-vector-search]] regarding embedding-based search approaches.

**Programmatic Tool Calling** (PTC) lets Claude orchestrate tools through code rather than individual API round-trips. In traditional tool calling, each invocation requires a full inference pass and every intermediate result enters Claude's context window. A budget compliance check across 20 employees would mean 20+ tool calls, 2,000+ expense line items in context, and Claude manually summing and comparing values in natural language. With PTC, Claude writes a Python script that calls tools, processes results, and outputs only the final answer. The intermediate data — those 2,000+ line items — never touches Claude's context. Results: 37% token reduction on complex research tasks, elimination of 19+ inference passes in 20-tool workflows, and improved accuracy from explicit code logic over natural language data juggling. Claude for Excel uses PTC to manipulate spreadsheets with thousands of rows without context window overflow.

The implementation is clean: mark tools with `allowed_callers: ["code_execution_20250825"]` to opt them into programmatic execution. Claude writes orchestration code that runs in a sandboxed Code Execution environment. When the code calls a tool, the API handles execution and returns results to the code environment rather than Claude's context. The tool request includes a `caller` field indicating it originated from code execution, and results feed back into the running script. Only the script's final `stdout` output enters Claude's context window — this is the same principle behind the session-as-context-object pattern in [[anthropic-managed-agents-architecture]], where context management is separated from storage.

**Tool Use Examples** address the gap between structural validity (JSON Schema) and usage correctness. Schemas define types and required fields but can't express when to include optional parameters, which combinations make sense, or what format conventions to follow. A `create_ticket` tool might accept `due_date` as a string, but "2024-11-06", "Nov 6, 2024", and "2024-11-06T00:00:00Z" are all valid strings. Adding `input_examples` to tool definitions shows Claude concrete usage patterns: three examples at different complexity levels teach format conventions, nested structure patterns, and parameter correlations. Internal testing showed accuracy improvement from 72% to 90% on complex parameter handling.

The three features are complementary and should be layered strategically based on the primary bottleneck. Context bloat from definitions → Tool Search Tool. Large intermediate results → PTC. Parameter errors → Tool Use Examples. For MCP servers, entire servers can be deferred with per-tool overrides: `default_config: {defer_loading: true}` with specific high-use tools set to `defer_loading: false`. The features are available under the `advanced-tool-use-2025-11-20` beta header and work with [[claude-sonnet-4-6-capabilities]] and later models.

## Key Concepts

- **Deferred tool loading** — Marking tools with `defer_loading: true` so their full definitions are excluded from the initial prompt but remain discoverable via search. Reduces context consumption by ~85% while maintaining access to the full tool library.
- **Programmatic Tool Calling (PTC)** — Claude writes Python code that orchestrates tool calls, processes intermediate results in a sandboxed environment, and returns only the final output to context. Eliminates inference passes between sequential tool calls.
- **Tool Use Examples** — Concrete `input_examples` added to tool definitions that show Claude usage patterns beyond what JSON Schema can express: format conventions, parameter correlations, and nested structure usage.
- **Context pollution** — The accumulation of intermediate tool results in Claude's context window, consuming tokens and potentially pushing important information out. PTC's primary problem to solve.
- **Agent-Computer Interface (ACI)** — The holistic design of tool definitions, documentation, and examples that determines how effectively an agent uses tools. Requires HCI-level investment.

## Related Articles

- [[pgvector-postgres-vector-search]] — Tool Search Tool uses similar vector-based discovery patterns for finding relevant tools from large libraries.
- [[anthropic-managed-agents-architecture]] — PTC's context isolation mirrors the session-as-context-object pattern where intermediate state lives outside Claude's context window.
- [[claude-sonnet-4-6-capabilities]] — The primary model for PTC workflows; cost-efficiency makes multi-tool orchestration economically viable.
- [[claude-opus-4-6-capabilities]] — Tool Search Tool accuracy improvements (49%→74%) measured on Opus 4, demonstrating that even frontier models benefit from reduced tool noise.

## Relevance to AgentNexLiFy

AgentNexLiFy's chat widget agent connects to 5+ services (Supabase, Stripe, Resend, Twilio, calendar APIs). Tool Search Tool should be adopted immediately — the current approach loads all tool definitions upfront, wasting context on tools rarely needed in any single conversation. The lead qualifier agent is the strongest PTC candidate: qualifying a lead involves checking business hours, searching the knowledge base, looking up appointment availability, and cross-referencing lead history — a multi-tool workflow where intermediate results don't need to enter context. Tool Use Examples should be added to the `create_lead` and `book_appointment` tool definitions, where parameter format ambiguity (date formats, phone number formats, timezone handling) currently causes occasional failures. Combined, these features could reduce per-conversation token cost by 30-50% while improving tool call accuracy.
