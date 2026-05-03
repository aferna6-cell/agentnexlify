---
paths:
  - "**/*"
---

# Knowledge Base First — Check Before Researching

## Rule
Before starting any research/analysis task, check `knowledge-base/wiki/` for relevant articles. Read `knowledge-base/INDEX.md` for topics.

## Why
- Articles compiled with embeddings via pgvector
- Semantic search via `/kb-query`
- Saves hours of re-research
- Knowledge compounds — every session adds to it

## After the task
- New knowledge → add via `/kb-ingest` or drop in `knowledge-base/raw/`
- Run `/kb-compile` to promote raw → wiki with embeddings
- Cross-link new article to existing (wikilinks)

## Categories
- Competitors
- AI/LLM developments
- Small Business SaaS
- Vertical industries (salon, plumber, dental, etc.)
- Technical patterns
- Regulations & compliance
- Growth & distribution

## Read order (cheapest → most expensive)
1. `knowledge-base/HOT.md` — 500-token rolling active-state cache. Read FIRST. Karpathy hot-cache pattern.
2. `knowledge-base/INDEX.md` — 44K full catalog of 110+ articles
3. Specific `wiki/<category>/<article>.md` if INDEX points to one
4. `raw/` only when wiki doesn't have it

## Pointers
- Hot cache: `/home/aidan/agentnexlify/knowledge-base/HOT.md`
- Index: `/home/aidan/agentnexlify/knowledge-base/INDEX.md`
- Wiki: `/home/aidan/agentnexlify/knowledge-base/wiki/`
- Raw sources (pending compile): `/home/aidan/agentnexlify/knowledge-base/raw/`

## Karpathy pattern
LLM Wiki replaces RAG's ephemeral retrieval with a persistent, self-maintaining wiki. Every new source updates multiple entity pages. See `wiki/ai-llm/llm-wiki-karpathy-pattern.md`.
