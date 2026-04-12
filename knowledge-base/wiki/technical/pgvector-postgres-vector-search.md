---
title: "pgvector — Native Vector Search in Postgres"
category: technical
tags: ["pgvector", "postgres", "embeddings", "semantic-search", "hnsw", "ivfflat"]
sources: ["raw/technical/github---pgvector-pgvector-open-source-vector-similarity-search-for-postgres-git.md"]
created: 2026-04-12
updated: 2026-04-12
summary: "pgvector is the open-source Postgres extension that powers AgentNexLiFy's knowledge-base semantic search; it supports six distance metrics, HNSW and IVFFlat indexes, and keeps embeddings colocated with relational data."
---

# pgvector — Native Vector Search in Postgres

pgvector is the open-source Postgres extension that stores and searches vector embeddings inside a normal relational database, without a separate vector store. AgentNexLiFy relies on it for the knowledge-base semantic search described in [[llm-wiki-karpathy-pattern]], where every compiled wiki article has a Voyage AI embedding stored in the `kb_articles` table alongside title, category, summary, and tags. The practical value is that the same Supabase Postgres instance that holds tenants, leads, messages, and appointments also holds the vector index, so semantic search runs in the same query as a tenant filter and a created-at range. No dual-write, no cross-store consistency problem, no extra vendor.

The extension supports single-precision, half-precision, binary, and sparse vectors, plus six distance functions: L2 distance (`<->`), negative inner product (`<#>`), cosine distance (`<=>`), L1 distance (`<+>`), Hamming distance (`<~>` for binary), and Jaccard distance (`<%>` for binary). For text embeddings from Voyage AI or Anthropic's forthcoming embedding service, cosine distance is the correct default — it's magnitude-invariant and matches how OpenAI, Voyage, and Cohere normalize embeddings internally. AgentNexLiFy uses `<=>` throughout the knowledge base. The negative-inner-product operator exists because Postgres indexes only support ascending order; flipping the sign lets the planner use an index scan for "highest inner product."

Indexes are the load-bearing part. pgvector offers two ANN index types: IVFFlat (inverted file with flat quantization) and HNSW (hierarchical navigable small world). HNSW is strictly better for the AgentNexLiFy use case: sub-10ms query latency at tens of thousands of vectors, no training step required, accurate recall at default parameters. IVFFlat is cheaper to build but requires a `lists` parameter tuned to dataset size and a training step on representative data. For the current knowledge-base scale (single-digit thousands of articles) either works; for the product roadmap where tenant-specific RAG over uploaded documents is planned, HNSW is the right default because each tenant's corpus is small and rebuild frequency matters more than memory footprint.

The installation path on Supabase is trivial — `CREATE EXTENSION vector;` — because pgvector ships preinstalled. See [[pgvector-implementation-guide]] for the hand-installation path on a self-managed Postgres, which requires `postgresql-server-dev-*` headers and a `make && make install` build. The GitHub README also notes Docker, Homebrew, APT, Yum, and conda-forge install paths, and that pgvector is preinstalled in Postgres.app and "many hosted providers." For AgentNexLiFy this means zero ops work: Supabase already has it, the `vector` type is available in every migration, and the only thing to decide per table is the dimension.

Dimensions are declared per column. The `kb_articles.embedding` column is `vector(512)` because Voyage AI's voyage-3-lite outputs 512-dimensional embeddings. If AgentNexLiFy later adds a second embedding model — say, a larger Voyage model for high-accuracy tenant-document retrieval — it would be a new column, not a replacement, so legacy embeddings don't need re-encoding on every model switch. The extension supports exact search (no index, full scan, highest recall) and approximate search (HNSW or IVFFlat, sub-linear query time, 95%+ recall at default parameters). Exact search is fine for the wiki's few thousand articles; the index becomes load-bearing at 100k+ vectors per tenant.

pgvector also supports hybrid queries: `WHERE client_id = $1 AND category = $2 ORDER BY embedding <=> $3 LIMIT 5`. This is the default pattern in AgentNexLiFy — tenant isolation via `client_id` (not `tenant_id`; see `.claude/rules/schema-discipline.md`) combined with vector similarity. The Postgres planner handles these cleanly because the filter columns are standard B-tree indexes, and the vector column's ANN index is consulted only for the top-k scan after filtering.

The main pgvector limitations, per the upstream documentation: performance below dedicated vector databases at the billion-vector scale, no GPU acceleration (CPU-only), and storage overhead proportional to vector dimension × row count. For AgentNexLiFy, none of these bite — the product runs in the tens of thousands of vectors total across the knowledge base and hundreds of thousands at most across all tenant RAG corpora combined, well within CPU-only territory.

## Key Concepts

- **Embedding** — A fixed-dimension numeric vector output by a model that encodes semantic meaning. Similar texts produce similar vectors under the chosen distance metric.
- **HNSW (Hierarchical Navigable Small World)** — A graph-based ANN index with logarithmic search time. No training step, fast build, low query latency. pgvector's recommended default index for most workloads.
- **IVFFlat (Inverted File, Flat quantization)** — An ANN index that partitions vectors into `lists` clusters and searches the nearest `probes` clusters at query time. Cheaper to build than HNSW but requires a training step and parameter tuning.
- **Cosine distance (`<=>`)** — Distance metric where 0 means identical direction and 2 means opposite direction. Magnitude-invariant. Default for text embeddings because most embedding models ship normalized vectors.
- **Hybrid query** — A single SQL statement that combines standard relational predicates (tenant filter, category filter, date range) with vector similarity ordering. pgvector's headline feature.

## Related Articles

- [[pgvector-implementation-guide]] — Step-by-step installation and first-query tutorial; this article covers the conceptual model, that one covers the mechanics.
- [[llm-wiki-karpathy-pattern]] — The knowledge-management pattern that pgvector enables inside AgentNexLiFy's Supabase.
- [[anthropic-mission-and-latest-releases]] — Claude is the LLM that generates the text this system embeds; pgvector is how that text becomes searchable.

## Relevance to AgentNexLiFy

pgvector is the single most important technical choice for the knowledge-base architecture, and the right one. Keeping embeddings in Supabase means tenant isolation, backups, migrations, and query planning are all solved problems. The product roadmap to add per-tenant document RAG (upload PDFs and Word docs into a tenant-scoped embedding table, retrieve via cosine distance at chat time) is a direct extension of the current `kb_articles` pattern: same extension, same index type, different dimension if the model changes. Action items: (1) ensure `kb_articles` has an HNSW index on `embedding` once the article count crosses 500, (2) standardize on cosine distance for all new vector columns, (3) never split embeddings into a separate vector store — the whole thesis here is that Postgres is sufficient up to the scale AgentNexLiFy will hit in the next three years.
