---
type: product
name: "Knowledge Base Wiki"
aliases:
  - "LLM Wiki"
  - "knowledge-base"
tags:
  - product
  - internal-tooling
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Knowledge Base Wiki

## Summary
An internal LLM-compiled wiki (Karpathy self-maintaining-wiki pattern) inside the agentnexlify
repo. ~114–117 articles with pgvector embeddings, recompiled raw→wiki twice daily. It is the
competitive-intel + domain-knowledge backbone and the precedent for this vault's design.

## Structure
- 8 categories: ai-llm, competitors, growth, regulations, small-biz-saas, technical, verticals,
  _outputs. `INDEX.md` catalog + `HOT.md` rolling active-state cache. Source: [[kb-index]]

## Why it matters here
- The per-tenant vertical KB is AgentNexLiFy's stated moat (see [[Vertical Knowledge-Base Moat]]).
- This vault deliberately mirrors its provenance-first, compile-then-canonicalize approach.

## Related
- [[AgentNexLiFy]] · [[Vertical Knowledge-Base Moat]] · [[Competitive Landscape]]

## Provenance
- [[kb-index]]
