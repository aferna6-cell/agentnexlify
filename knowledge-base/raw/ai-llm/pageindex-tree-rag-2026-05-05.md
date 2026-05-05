# PageIndex (Vectify AI) — Tree-Based RAG Assessment

**Captured:** 2026-05-05
**Status:** Watch — not adopt
**Source:** Social media claim (X/Twitter), Vectify AI blog + GitHub
**Claim under review:** "Entire RAG industry about to get cooked. PageIndex: no vector DB, no embeddings, no chunking, no similarity search. 98.7% on FinanceBench."

## What PageIndex actually is

Hierarchical / agentic RAG. Builds a tree index over a document (sections → subsections → leaves). At query time the LLM reasons through the tree like a human reading a table of contents — chooses which branch to descend, retrieves leaf content, answers.

Not a paradigm shift. Sits in the same family as:
- **RAPTOR** (Stanford, 2024) — recursive abstractive tree retrieval
- **GraphRAG** (Microsoft, 2024) — knowledge-graph traversal RAG
- **Contextual Retrieval** (Anthropic, 2024) — chunk + context prefix
- **Agentic RAG** — LLM-driven retrieval orchestration (broad pattern)

PageIndex is one execution of tree-walk retrieval, open source, Vectify AI.

## What's actually true vs hype

| Claim | Reality |
|---|---|
| "No vector DB" | True for retrieval. Index = tree of summaries + raw sections. |
| "No embeddings" | True for retrieval. Trades vector cost for inference cost. |
| "No chunking" | Partially true. Documents are split at structural boundaries (sections), which IS a form of chunking — just hierarchy-aware not fixed-window. |
| "No similarity search" | True. Tree descent driven by LLM judgment. |
| "98.7% FinanceBench" | Vendor-reported, not independent eval. Treat as upper bound. |
| "Industry cooked" | False. Latency + token cost don't scale to 10M+ docs or low-latency UX. |

## Honest tradeoffs

**Wins where:**
- Single long structured document (10-K, contract, textbook, RFC)
- Hierarchy is real (ToC, numbered sections)
- Query volume low, latency tolerance high
- Recall over a known doc beats keyword/cosine

**Loses where:**
- Corpus has no structure (Slack dumps, support tickets, chat logs)
- High query throughput (every query = multi-hop LLM calls)
- Latency-sensitive (user-facing chat, widget reply)
- Cost-sensitive batch (10k queries/day on Opus = $$)

**Cost shift:** vector RAG burns embedding cost upfront + cheap retrieval at query. PageIndex burns inference cost on every query. Neither is free.

## AgentNexLiFy applicability

| Surface | Verdict | Reasoning |
|---|---|---|
| Widget chat reply | NO | Latency-sensitive (<2s target). Tree-walk = multi-hop LLM = 5-15s. Kills UX. |
| Tenant KBs (`widget/knowledge-bases/<tenant>_kb.md`) | MAYBE | Small structured docs. Worth a spike if pgvector recall complaints surface. Currently no complaints logged. |
| Project KB wiki (`knowledge-base/wiki/`) | NO | Already on pgvector + contextual retrieval. Working. Don't swap working infra. |
| Compound-engineering doc retrieval | NO | Not a retrieval bottleneck currently. |
| Onboarding intake docs (PRD, contracts) | MAYBE | Long structured docs, low query volume. Fits PageIndex shape. Out of scope for now. |

## Decision

**Action: log as "watch", no install, no spike.** Re-evaluate when ANY of:
1. Tenant KB recall complaints reach critical threshold (>3 reports of "widget didn't find answer")
2. New product surface with long structured docs + low query volume (compliance docs, contract review)
3. Independent benchmark replicates the 98.7% number on FinanceBench
4. Latency drops 5x via better tree-walk algorithms

## References
- GitHub: https://github.com/VectifyAI/PageIndex
- Vectify AI blog (vendor source for 98.7% claim)
- RAPTOR paper (predecessor): https://arxiv.org/abs/2401.18059
- Anthropic Contextual Retrieval: https://www.anthropic.com/news/contextual-retrieval

## Cross-refs
- `knowledge-base/wiki/` — current pgvector RAG (working)
- `widget/knowledge-bases/` — per-tenant KB pattern
- `.claude/rules/model-routing.md` — Haiku for simple retrieval, Sonnet/Opus for tree-walk reasoning
