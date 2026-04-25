---
title: "Writing Effective Tools for AI Agents — Anthropic's Five Principles"
category: ai-llm
tags: ["anthropic", "tool-use", "mcp", "agent-design", "prompt-engineering", "tool-descriptions", "namespacing", "token-efficiency"]
sources: ["raw/ai-llm/anthropic-writing-tools-for-agents-2026-04-25.md"]
created: 2026-04-25
updated: 2026-04-25
summary: "Anthropic's evaluation-driven playbook for designing agent tools — consolidate over wrap, namespace by service+resource, return semantic identifiers, cap responses at ~25k tokens, and treat tool descriptions as prompt-engineered surface."
---

# Writing Effective Tools for AI Agents — Anthropic's Five Principles

Anthropic's engineering team published the playbook they used to optimize their own internal MCP tools using Claude Code as the iterative reviewer. The thesis: tools are a contract between deterministic code and non-deterministic agents, so they cannot be designed like ordinary APIs. The five principles distilled from the post — choose the right tools, namespace them, return meaningful context, optimize token efficiency, and prompt-engineer the descriptions — are immediately actionable for AgentNexLiFy's own MCP surface and for the tool definitions inside our managed agents.

The first principle inverts how most engineers approach tooling. More tools is the common error. The default impulse is to wrap every existing API endpoint as its own tool, which is what produces the bloated 100-tool MCP surfaces that confuse agents and waste context. Anthropic argues for a small set of tools that consolidate multi-step workflows. Their canonical examples: replace `list_users` + `list_events` + `create_event` with a single `schedule_event` tool that handles availability and booking under the hood; replace `read_logs` with `search_logs` that returns only relevant lines plus surrounding context; replace `get_customer_by_id` + `list_transactions` + `list_notes` with `get_customer_context` that compiles everything in one call. The principle is that a tool should match a unit of agent intent, not an API endpoint.

Namespacing matters more than expected. With dozens of MCP servers in play, agents need clear boundaries to pick the right tool. Anthropic uses prefix-based namespacing by service and resource: `asana_search`, `asana_projects_search`, `asana_users_search`. Their internal evaluations showed non-trivial differences between prefix and suffix conventions, varying by model — meaning every team should pick a convention via evaluation rather than aesthetic preference. The lesson connects to [[agent-skills-anthropic]]: progressive disclosure of tools through namespace prefixes lets the model navigate without loading every tool's full description into context.

Returning meaningful context separates good tools from bad ones. Anthropic found that resolving cryptic UUIDs to natural-language names or zero-indexed IDs significantly improves Claude's retrieval precision. Tool responses should privilege fields like `name`, `image_url`, `file_type` over `uuid`, `256px_image_url`, `mime_type`. Where flexibility is needed (e.g., `search_user(name='jane')` followed by `send_message(id=12345)`), they recommend exposing a `response_format` enum with `concise` and `detailed` values — Anthropic's example showed 206 tokens for detailed vs 72 tokens for concise on the same record. Response structure (XML, JSON, Markdown) also affects performance because LLMs are trained on next-token prediction and perform better on structures matching their training data; the optimal format must be selected via evaluation, not assumed.

Token efficiency is enforced at Anthropic with a 25,000-token default cap on tool responses inside Claude Code. Pagination, range selection, filtering, and truncation are required for any tool that could blow past that ceiling. When responses are truncated, the truncation message itself should steer the agent toward a more targeted strategy — many small searches over one broad search — rather than just dumping the cutoff. Error responses get the same treatment: opaque error codes and tracebacks waste turns, while helpful errors that name the specific input field and suggest a fix close the loop in a single retry. This connects directly to [[effective-context-engineering]], which frames context as a finite attention budget that tool design must respect.

The fifth principle is the highest-leverage one. Tool descriptions are loaded into the agent's context every turn, so prompt-engineering them yields outsized returns. Anthropic's example: Claude Sonnet 3.5 hit state-of-the-art on SWE-bench Verified after precise tool-description refinements — same model, same code, just better descriptions. The mental model: write descriptions for a new hire on your team, not for a developer reading API docs. Specialized query formats, niche term definitions, and resource relationships should be made explicit. Parameter names should be unambiguous (`user_id`, not `user`). Anthropic also disclosed that Claude was appending `2025` to its web search tool's query parameter unnecessarily, biasing results — fixed entirely by improving the tool description.

The methodology behind all five principles is evaluation-driven. Anthropic recommends 20+ realistic prompt-response pairs per tool, paired with verifiers (string match or LLM-as-judge), measured across accuracy, runtime, total tool calls, token consumption, and error counts. Their key trick: concatenate evaluation transcripts and paste them into Claude Code, which is "an expert at analyzing transcripts and refactoring lots of tools at once." Most of the principles in the post came from this exact loop — Claude Code optimizing Anthropic's internal tools against held-out test sets. The same loop is available to anyone with an MCP server and an evaluation harness, which makes this less a "best practices" doc and more a benchmark for tool maturity.

## Key Concepts

- **Tool consolidation** — Replacing N small tools with one tool that handles a multi-step workflow under the hood. Reduces context cost, hallucination risk, and agent decision fatigue.
- **Namespacing** — Grouping related tools under common prefixes (e.g., `service_resource_action`) to delineate boundaries and reduce ambiguity when many tools are loaded.
- **Response format enum** — A parameter exposed in the tool spec (`concise` / `detailed`) letting the agent control verbosity. Anthropic measured 65% token reduction between modes on the same payload.
- **Tool description prompt engineering** — Treating the description text as part of the system prompt and iterating on it like any other prompt component. Small refinements move benchmark numbers materially.
- **Evaluation-driven tool development** — A loop of prompt generation, agentic execution, metric collection, and Claude-Code-assisted analysis that produces measurable tool improvements per iteration.

## Related Articles

- [[anthropic-building-effective-agents]] — Anthropic's broader pattern catalog for agent workflows; this article is the tool-layer companion.
- [[agent-skills-anthropic]] — Progressive disclosure pattern for capabilities; complements namespacing as a context-management lever.
- [[anthropic-advanced-tool-use]] — Tool Search Tool, Programmatic Tool Calling, and Tool Use Examples; production features that lean on the same principles.
- [[effective-context-engineering]] — Frames the finite attention budget that motivates token-efficient tool responses.
- [[claude-code-best-practices]] — Claude Code is the recommended tool-evaluation reviewer in this post.

## Relevance to AgentNexLiFy

Three concrete actions follow. First, audit the current MCP surface against the consolidation principle — places where the agent makes 3+ tool calls to assemble customer state are candidates for a `get_customer_context`-style consolidator, especially around lead lookups in `backend/services/lead_qualifier.py` and conversation context in `backend/services/chat_service.py`. Second, the `response_format: concise|detailed` enum is a low-effort win for the widget chat flow — most turns need only the concise form, which would cut input tokens to Claude meaningfully and stack with [[claude-prompt-caching-5min-ttl-2026]] for compounding cost reduction. Third, the prompt-engineered tool description guidance applies to every internal MCP server we maintain (Supabase MCP wrappers, Stripe wrappers); investing one focused session in rewriting tool descriptions with explicit input semantics, niche term definitions, and unambiguous parameter names is likely the highest-ROI single change available to our managed-agent stack right now.
