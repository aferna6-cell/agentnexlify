---
title: "Memory for AI Agents — Three Architectures and the Ethics of Forgetting"
category: ai-llm
tags: ["agent-memory", "context-engineering", "vector-store", "temporal-knowledge-graph", "mem0", "zep", "letta", "context-rot"]
sources: ["raw/ai-llm/tns-memory-ai-agents-context-engineering.md"]
created: 2026-04-18
updated: 2026-04-18
summary: "TNS 2026 survey maps three agent-memory architectures (vector retrieval, rolling summarization, temporal knowledge graph) and the extraction-consolidation-retrieval pipeline; Zep reports +18.5% long-horizon accuracy and ~90% latency cut, Mem0 reports +26% on memory benchmarks."
---

# Memory for AI Agents — Three Architectures and the Ethics of Forgetting

LLMs are stateless by default. Every call starts from zero unless the harness replays history into the context window. This works for short interactions and breaks as soon as workflows span days, departments, or accounts. Nicole Seah's January 2026 TNS survey argues that the industry has converged on a specific problem — context rot from ballooning token windows — and three competing architectures for solving it. The stakes are practical: a sales copilot that remembers prior conversations cuts research time in half; a customer-service agent with durable recall lowers churn; a marketing copilot that retains buyer intent qualifies leads better. Memory is not a feature; it is the infrastructure layer that determines whether an agent stays useful past turn five.

Context rot is the failure mode that kicked off the current wave. The promise in 2023–2024 was that longer context windows would obviate memory — just put everything in the prompt. Real workloads broke that promise: performance degraded as contexts got larger, retrieval cost compounded, and token bills ballooned. Human memory evolved as a layered system (working, short-term, long-term) precisely because holding everything in working memory is impossible. Agents need the same: compress, abstract, forget, and retrieve only what matters now. The context-engineering discipline that emerged in 2025 treats the context window as a budget to curate, not a bucket to fill. This maps directly to the task-budget discipline in Claude Opus 4.7 (see [[claude-opus-4-7-release]]) where the model paces output against an advisory token budget.

Three architectures now dominate. The **vector-store approach** (Pinecone, Weaviate, pgvector) embeds past interactions and retrieves by cosine similarity — fast, simple, surface-level. The **summarization approach** (rolling transcript summaries) compresses conversations into narrative summaries that re-inject at each turn — reduces tokens but loses specific facts. The **temporal knowledge graph approach** (Zep) encodes memories as nodes and edges: people, places, events, times. Zep's published benchmarks show +18.5% long-horizon accuracy over baseline retrieval while cutting latency by ~90%. Mem0 takes a fourth path — structured summarization with explicit conflict resolution — and reports +26% accuracy gains on memory benchmarks with lower token cost. Letta published a counter-result: a raw filesystem of text files indexed by timestamp outperforms several specialized systems, reinforcing the "simplicity wins" pattern documented in [[anthropic-building-effective-agents]].

The pipeline underneath all three architectures has the same three stages. **Extraction** identifies which facts matter; Mem0 uses a "memory candidate selector," Zep encodes entities and relationships, Letta relies on time-based indexing. **Consolidation** rewrites older memories when new evidence appears, preventing the context drift where outdated facts persist as canon. **Retrieval** weights relevance by recency and importance and injects only the top-k into the context window. Systems that skip consolidation hallucinate old facts; systems that skip extraction bury signal in noise. The three-stage pipeline is the minimum viable memory architecture — below this bar, you have log-replay, not memory.

The governance layer is where most production deployments go wrong. Enterprises want memory dashboards — "what does the agent remember about this customer, why does it think that, and how do we delete it?" Stored embeddings are personal data under GDPR whether or not the data is explicit text. A vector that uniquely identifies a person's query pattern is re-identifiable. The doctrine in [[ftc-auto-dealers-deceptive-pricing-2026]] hints at a parallel direction — regulators treat durable state as a first-class compliance surface. The practical response is architectural: encryption at rest, scoped retention, per-tenant deletion APIs, and audit trails that show what the agent recalled when. "Native features, not afterthoughts," Seah writes, and the cost of retrofitting these into an existing vector store is substantial.

The near-term trajectory is middleware. `memory.write()` will become as routine as `db.save()`. Vertical agent platforms will bundle memory providers by default. Memory dashboards will surface learned facts with edit/erase controls. Longer term, agents develop institutional personalities — records of collaboration, user preferences, even mood. That anchors trust but raises the question Seah closes on: when a model fine-tuned on your interactions generates insight, whose memory is it? For AgentNexLiFy, the answer matters at the tenant/end-customer boundary. A widget that remembers a returning customer's prior booking preference improves the product; a widget that leaks one customer's pattern into another tenant's context is a data breach.

## Key Concepts

- **Context rot** — Degradation of model performance as context window fills, even when context is technically within the model's stated limit. Motivates memory layers that curate rather than dump.
- **Temporal knowledge graph** — Memory architecture (Zep) that stores entities and time-stamped relationships between them. Captures "who said what about whom and when"; outperforms flat retrieval on long-horizon questions.
- **Memory candidate selector** — Mem0's component that identifies atomic salient statements from conversation turns for storage; prevents log-dumping at extraction.
- **Consolidation / re-encoding** — Pipeline stage where the system rewrites older memories when new evidence appears, preventing persistent outdated facts. Analogous to human memory reconsolidation.
- **Memory as governance surface** — Treating agent memory as a first-class compliance artifact with dashboards, edit/erase controls, and audit trails. Required for GDPR/CCPA compliance on embedding-backed state.

## Related Articles

- [[anthropic-building-effective-agents]] — Pattern catalog that complements memory-layer thinking; orchestrator-workers and evaluator-optimizer patterns compose with durable memory.
- [[anthropic-contextual-retrieval]] — Embedding-time context prepending that reduces retrieval failure; combines with any of the three memory architectures described here.
- [[encore-pgvector-guide-2026]] — Infrastructure backing for the vector-store memory approach at realistic scale.
- [[claude-opus-4-7-release]] — Opus 4.7 task budgets encode the same "context as budget, not bucket" discipline at the model layer.
- [[ftc-auto-dealers-deceptive-pricing-2026]] — Regulatory pattern that will plausibly apply to durable AI state; memory dashboards become compliance primitives.
- [[mit-ai-chatbot-vulnerable-users-2026]] — Memory amplifies baseline model bias by caching demographic inferences; cross-article caveat.

## Relevance to AgentNexLiFy

Our widget is the exact use case where memory compounds. A returning customer at a dental tenant who already gave their insurance info, preferred appointment window, and dentist should not re-answer those questions. Three practical directions: (1) Pick the architecture deliberately — pgvector retrieval is already in place via `kb_articles`; the near-term upgrade is a per-end-customer scoped memory layer with rolling summarization at session close, not a temporal knowledge graph (overkill for small-business conversational scope). (2) Wire extraction + consolidation as first-class pipeline steps, not implicit side effects; a "memory candidate selector" sits between the widget response and the persistence layer and rejects noise. (3) Treat memory as a governance surface from day one — every tenant needs a "what we remember about this customer" dashboard and a deletion API, because the moment a tenant asks for it in a demo we need to have built it. The Mem0 and Zep benchmarks suggest +18-26% quality gains for real workloads; those gains matter to retention and directly fight GHL's "keeps remembering your customers" positioning.
