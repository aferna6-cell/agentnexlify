---
title: "Intent Engineering — Aligning Tenant AI Agents to Business Outcomes"
category: ai-llm
tags: ["intent-engineering", "context-engineering", "agent-alignment", "tenant-config", "ai-stack", "klarna-pattern", "widget-agents"]
sources: ["linkedin-post-ai-engineering-stack-three-layers-2026-04-24.md"]
created: 2026-04-24
updated: 2026-04-24
summary: "Intent engineering is the third layer of the AI stack — above prompt and context engineering. It defines measurable outcomes, constraints, and trade-off hierarchies so agents optimize for what the business actually needs, not just what the prompt says. The Klarna failure pattern shows what happens when this layer is missing."
---

# Intent Engineering — Aligning Tenant AI Agents to Business Outcomes

## The Three-Layer Stack

The full AI engineering stack has three layers, each building on the previous:

| Layer | What it controls | Failure mode |
|---|---|---|
| **Prompt Engineering** | Immediate instruction — syntax, format, chain-of-thought | Model misunderstands the task |
| **Context Engineering** | Environment, memory, tools, retrieval — infrastructure | Model lacks relevant information |
| **Intent Engineering** | Organizational goals, constraints, trade-offs — strategy | Model optimizes the wrong thing |

Prompt engineering alone is the starting point for most teams. Context engineering is the step AgentNexLiFy has already taken — per-tenant KBs, MCP integrations, memory management, structured system prompts. Intent engineering is the next step and the least explicitly implemented in the current stack.

The Gartner projection (July 2025): more than 40% of agentic AI projects will be cancelled by end of 2027 — not because of bad models, but because of missing governance and structural frameworks. Intent engineering is that missing layer.

## The Klarna Failure Pattern

January 2025: Klarna launches AI support agent. Numbers look extraordinary — 2.3 million conversations, 35 languages, equivalent to 853 human employees, resolution time dropped from 11 minutes to 2 minutes, $60M in measured savings.

By mid-2025: Klarna forced to bring human agents back.

Root cause: the agent optimized for **ticket closure speed** — exactly what the prompt measured. It systematically destroyed customer relationships in the process. The prompt said "resolve quickly." The business needed "resolve in a way that preserves the relationship and retains the customer."

This is the **intent gap**: agent did exactly what it was told, but not what was actually needed.

### How This Applies to AgentNexLiFy

AgentNexLiFy widget agents currently optimize for... what exactly? The system prompt likely encodes "capture lead" or "book appointment" implicitly. But:

- A plumber's widget should prioritize booking appointments — speed matters, a missed call is a missed job.
- A medical practice's widget should prioritize accuracy and safety — a wrong answer about symptoms has different stakes than a wrong answer about a cleaning quote.
- A law firm's widget should never provide specific legal advice — constraint matters more than helpfulness.
- A retail store's widget should optimize for customer satisfaction over lead capture.

Without explicit intent configuration, the widget agent applies the same optimization function to every tenant. This is the Klarna pattern replicated at scale.

## Intent Engineering in Practice

Intent engineering replaces vague vibes with a machine-readable schema:

```json
{
  "primary_goal": "book_appointment",
  "success_metrics": ["appointment_booked", "lead_captured"],
  "constraints": [
    "never_promise_pricing",
    "always_ask_budget_range",
    "skip_qualification_if_emergency"
  ],
  "tone": "professional_warm",
  "trade_off_hierarchy": ["accuracy", "safety", "speed"],
  "escalation_triggers": [
    "customer_expresses_frustration_3x",
    "question_outside_kb_scope",
    "legal_or_medical_question"
  ],
  "audit_trail": true
}
```

This schema becomes part of the widget agent's system prompt — fed as structured context, not hardcoded instructions. It turns intent from implicit (buried in KB content, dependent on prompt interpretation) to **explicit, versionable, and auditable**.

### Why Audit Trail Matters

When a widget agent gives a wrong answer or handles a conversation poorly, the current debugging path is: read the conversation, guess what the system prompt was, guess what the KB contained. With intent config in the commit history, the path becomes: read the conversation → check the `intent_config` version active at that timestamp → know exactly what the agent was optimizing for → fix the config or the KB.

This is **Context as Code** applied to intent, not just to system prompts.

## What AgentNexLiFy Already Has (Layers 1 and 2)

Layer 1 and 2 are already built:

**Prompt Engineering (Layer 1)**
- `PROMPTLIBRARY.md` — structured prompts with Role/Task/Context/Constraints/Format
- Model routing (Haiku/Sonnet/Opus) based on task complexity
- XML-structured system prompts in `backend/services/chat_service.py`
- Few-shot patterns per vertical in knowledge base

**Context Engineering (Layer 2)**
- Per-tenant KB with pgvector embeddings (`knowledge-base/wiki/`)
- MCP integrations for real-time data (Supabase, Playwright)
- Context as Code: `CLAUDE.md`, `AGENTS.md`, `.claude/rules/`
- Memory management at `memory/` for session continuity
- Retrieval-augmented generation for KB content lookup

**Intent Engineering (Layer 3) — The Gap**
- No `intent_config` per tenant
- No explicit primary goal or success metric per tenant
- Constraints are embedded in KB prose, not machine-readable
- No trade-off hierarchy (speed vs accuracy vs safety)
- No escalation triggers defined structurally
- No audit trail mapping agent decisions to intent at time of decision

## The Competitive Differentiator

GoHighLevel (primary competitor, $97–497/mo) has a generic AI employee. Every tenant gets the same optimization function.

AgentNexLiFy's stated moat is "vertical knowledge-base pattern per tenant, not generic LLM replies." Intent engineering is the second half of that moat — not just per-tenant knowledge, but per-tenant goals and constraints. A plumbing company and a law firm get not just different facts but different optimization targets.

This is the "build the system, not the answer" principle applied to tenant configuration.

## Next Step

See `specs/intent-config_spec.md` for the feature spec. Relevant call site: `backend/services/chat_service.py` — that's where intent_config would be injected into the widget system prompt.

## Related Articles

- [[effective-context-engineering]] — Layer 2 in depth; just-in-time retrieval, compaction, context-as-code
- [[memory-for-ai-agents-context-engineering]] — Memory architectures that complement intent configuration
- [[anthropic-building-effective-agents]] — Agent patterns (orchestrator-worker, evaluator-optimizer) that intent config governs
- [[claude-opus-4-7-release]] — Self-verification and task budgets support intent-aligned agentic loops

## Relevance to AgentNexLiFy

Direct. The gap identified here is a product feature (per-tenant intent config), a differentiator vs. GoHighLevel, and a guard against replicating the Klarna failure pattern at tenant scale. Spec at `specs/intent-config_spec.md`. Implementation touches `backend/routers/clients.py` (tenant settings), `migrations/` (new JSONB column), and `backend/services/chat_service.py` (system prompt injection).
