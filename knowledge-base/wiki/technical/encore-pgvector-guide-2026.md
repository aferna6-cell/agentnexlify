---
title: "You Probably Don't Need a Vector Database — pgvector at Realistic Scale"
category: technical
tags: ["pgvector", "postgres", "rag", "hnsw", "ivf", "infrastructure-consolidation", "latency-budget"]
sources: ["raw/technical/encore-pgvector-guide-2026.md"]
created: 2026-04-18
updated: 2026-04-18
summary: "Encore's 2026 teardown argues most RAG workloads (≤1M vectors) run fine on pgvector with <20ms HNSW query time and >95% recall; LLM generation at 500ms-3s makes the 2ms-vs-10ms vector-DB latency gap invisible, and transactional consistency beats sync pipelines."
---

# You Probably Don't Need a Vector Database — pgvector at Realistic Scale

Most backend teams bolt a dedicated vector database onto their existing Postgres the moment they add an AI feature. Encore's March 2026 teardown (Ivan Cernja, encore.dev) argues that for the workloads teams actually have — documentation search over 30,000 entries, support-ticket classification at 50,000 embeddings, internal knowledge bases in the low millions — running pgvector inside Postgres is both simpler and within noise of a purpose-built service. The operational case is the real argument: documents and vectors live in the same table under the same transaction, so a document insert and its embedding insert either both commit or both fail, and a semantic-search feature touches two services instead of three.

The performance case is easier than teams assume. pgvector supports cosine distance (`<=>`), L2 (`<->`), and inner product (`<#>`) with both HNSW and IVF indexing. HNSW builds a multi-layer graph where each vector points to neighbors, searches hop through edges toward the query, and returns approximate results at recall rates above 95% with default settings. At 1M vectors, HNSW queries come back in under 20ms. The vector step is almost never the bottleneck in a RAG pipeline — the embedding API call is 100-300ms, the LLM generation is 500ms-3s, so the 2ms-vs-10ms gap between a dedicated vector DB and pgvector is invisible to the user. Optimizing the part of the pipeline that takes a hundred times less time is a misreading of the latency budget.

The infrastructure case is where the real cost sits. A dedicated vector DB adds another deployment, another credential, another monitoring dashboard, another failure domain. A semantic search feature then touches three services: Postgres for documents, the vector DB for embeddings, and the embedding API. Each pair needs its own connection handling, retry logic, and consistency story. When you add a document, you write to both DBs; when you delete one, you delete from both; if one write fails you end up with a document missing its embedding or an orphaned vector. With pgvector, it's a single `INSERT` — documents, metadata, and embedding land in the same row under the same transaction, and any `JOIN` against application data is a normal SQL query. Metadata filters run before the similarity search, which is impossible or expensive to replicate when the two stores are physically separate.

The limits are real but narrow. Dedicated vector databases still win at billions of vectors, at massive real-time write throughput with continuous index rebuilds, and at advanced multi-tenant filtered search with per-tenant physical isolation and managed auto-scaling. If the product is the next Perplexity, an internet-scale search engine, or an embedding store serving thousands of enterprise tenants with independent SLAs, pgvector is not the answer. For every other shape of workload — which is most of them — pgvector covers the use case and removes a service. The RAG pipeline described in [[anthropic-contextual-retrieval]] (embed query, top-k search, retrieve, assemble prompt, generate) runs end-to-end on one SQL statement, one embedding call, and one LLM call.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536)
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

SELECT id, title, 1 - (embedding <=> $1) AS similarity
FROM documents
ORDER BY embedding <=> $1
LIMIT 5;
```

## Key Concepts

- **HNSW (Hierarchical Navigable Small World)** — A multi-layer graph index where each vector points to its neighbors. Search starts at a random entry point and hops through edges toward the query, narrowing in through progressively denser layers. Default pgvector index for high-recall similarity search.
- **IVF (Inverted File Index)** — An alternative pgvector index that partitions the vector space into clusters; at search time, only the clusters nearest the query get scanned. Faster to build, slightly lower recall than HNSW.
- **Distance metric selection** — Cosine similarity ignores magnitude and is the default for text embeddings. L2 is for magnitude-aware spaces. Inner product is cheaper and equivalent to cosine on normalized vectors. Most embedding models produce normalized output by default.
- **Transactional consistency** — With pgvector, document and embedding live in one row; an `INSERT` is atomic. With a separate vector DB, two writes can diverge and you need a reconciliation job.
- **Latency budget misreading** — The common mistake of optimizing the 2-10ms vector-search step when the embedding call (100-300ms) and LLM generation (500ms-3s) dominate end-to-end latency.

## Related Articles

- [[pgvector-postgres-vector-search]] — AgentNexLiFy's existing pgvector primer; overlaps with this article on distance metrics and index types, complements on indexing detail.
- [[pgvector-implementation-guide]] — Hands-on install + psycopg2 wiring for self-managed Postgres; the "how" to this article's "why."
- [[anthropic-contextual-retrieval]] — RAG pipeline design that runs end-to-end on pgvector without a dedicated vector service.
- [[memory-for-ai-agents-context-engineering]] — Memory architectures that use vector stores; same infrastructure-consolidation argument applies.

## Relevance to AgentNexLiFy

AgentNexLiFy's knowledge base already runs on pgvector via Supabase (`kb_articles.embedding vector(512)` per `migrations/081-kb-articles-and-sources.sql`). This article validates that architectural choice at realistic scale — our wiki plus per-tenant KB will not cross the 1M-vector line for years, and HNSW at sub-20ms is well inside our widget-latency budget (since first-token latency on Claude Sonnet 4.6 dominates). The direct implication: do not migrate to Pinecone, Weaviate, or Chroma when tenant count scales. Instead, invest in pgvector tuning (HNSW `m`/`ef_construction`, per-category partitioning, metadata filters pushed down before similarity search) and keep embeddings in Supabase next to tenant data with RLS. This preserves transactional consistency with `client_id` / `tenant_id` isolation and avoids a second service in the critical path.
