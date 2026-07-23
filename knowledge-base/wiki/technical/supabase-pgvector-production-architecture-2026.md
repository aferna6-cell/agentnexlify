---
title: "Supabase pgvector Production Architecture — Pooling, HNSW Sizing, and Failure Modes"
category: technical
tags: ["pgvector", "supabase", "hnsw", "pgbouncer", "scaling", "multi-tenant"]
sources: ["raw/technical/markaicode-supabase-pgvector-production-architecture-2026.md"]
created: 2026-07-23
updated: 2026-07-23
summary: "Six months of production experience with 10M vectors at 500 qps: HNSW (m=16, ef_construction=200) hits 8ms p95 vs 45ms for IVFFlat, transaction-mode PgBouncer served 500 concurrent searches on 20 connections, batched inserts run 16x faster than singles, and the two real-world failures were pool exhaustion and index bloat from missing REINDEX."
---

# Supabase pgvector Production Architecture — Pooling, HNSW Sizing, and Failure Modes

A May 2026 production writeup (10M 768-dim vectors, 500 qps, six months on AWS RDS) supplies the operational numbers missing from most pgvector guides. Its core claim: "the most failed architectural choice is storing embeddings in the same Postgres instance as your transactional data without isolation." The reference architecture separates concerns — PgBouncer in transaction mode in front of a primary with pgvector, read replicas for search traffic, and an async queue (BullMQ) batching embedding inserts so index maintenance never contends with query load. This extends the setup-level guidance in [[pgvector-implementation-guide]] and [[encore-pgvector-guide-2026]] with scaling and failure data.

The index numbers are concrete: HNSW with `m = 16, ef_construction = 200` on 10M vectors delivers 8ms p95 at 100 qps versus 45ms for IVFFlat with 4096 lists. The cost is memory — HNSW needs ~8x vector size in RAM, budgeted as 16 GB per 10M vectors; IVFFlat remains the right call under 1M vectors or in memory-limited environments. Scaling tiers: <10 qps/<1M vectors on a single primary (25ms p95), 100 qps/10M on 1 primary + 3 replicas (12ms), 1000 qps/100M sharded with 10 replicas (8ms). Notably for multi-tenant systems, the partitioning recommendation is by `tenant_id` (or `created_at`) to shrink per-replica index size, and RLS on the embeddings table via metadata matching is the prescribed isolation pattern.

Two mechanisms carried the load. Transaction-mode PgBouncer (`default_pool_size = 20`, `max_client_conn = 1000`) "sustained 500 concurrent search queries with only 20 database connections, cutting Postgres CPU utilization by half." And write batching — accumulating 1,000 embeddings per multi-row INSERT — ran at 5,000 embeddings/sec versus 300/sec for single inserts ("processed batch of 1000 embeddings in 120ms"), reducing both round trips and index fragmentation. The latency budget is also honest: embedding generation dominates at ~150ms p50, database search plus pooling is ~11ms, network ~2ms — meaning retrieval-speed optimization should start with the embedding call, not the database (relevant to the model choices in [[embedding-model-pricing-comparison-2026]]).

The failure catalog is the most reusable part. The two failures actually hit in production: connection-pool exhaustion under a marketing-campaign spike (fixed within an hour by adding PgBouncer + replicas) and index bloat causing query timeouts because `REINDEX` was never scheduled (now nightly at 2 AM). The full table: index bloat (detect via `pgstattuple` >30% dead tuples), pool exhaustion (PgBouncer rejections), embedding drift after model updates (recall drops — revalidate and regenerate), replication lag >5s under batch inserts, and OOM from HNSW memory. Cost framing: Supabase Pro at $25/mo beats Pinecone's $70/mo starter at moderate scale, but above ~100M vectors or strict SLAs the operational burden flips the equation.

## Key Concepts

- **Transaction-mode pooling** — PgBouncer reassigns connections per transaction, letting hundreds of concurrent clients share tens of Postgres connections; the highest-leverage pgvector scaling move.
- **HNSW memory rule** — ~8x vector size in RAM; 16 GB per 10M vectors of headroom, or OOM kills the instance.
- **Index bloat** — dead tuples from frequent inserts degrading ANN query times; detect with `pgstattuple`, fix with scheduled `REINDEX`.
- **Embedding drift** — distribution shift after an embedding-model update that silently degrades recall; requires benchmark validation and regeneration.
- **Tenant partitioning** — splitting the embeddings table by `tenant_id` to bound per-partition index size and align with RLS isolation.

## Related Articles

- [[pgvector-implementation-guide]] — the implementation baseline this article extends with production sizing and failure modes.
- [[encore-pgvector-guide-2026]] — complementary indexing guidance at smaller scale.
- [[embedding-model-pricing-comparison-2026]] — embedding-generation cost/latency, which this article shows dominates the retrieval latency budget.
- [[techsynth-pgvector-supabase-semantic-search]] — semantic-search query patterns running on top of this architecture.

## Relevance to AgentNexLiFy

Our `kb_articles` pgvector table is orders of magnitude below these thresholds (hundreds of rows, 512-dim voyage-3-lite), so the direct action list is small but real: (1) no HNSW urgency — at our scale sequential scan or IVFFlat is fine, and the 150ms embedding-generation cost dominates anyway; (2) when tenant KBs scale to many tenants × many chunks, adopt the `tenant_id` partitioning + RLS-on-embeddings pattern from day one rather than migrating later — it matches our client_id isolation invariant; (3) if we ever batch-embed tenant documents, use multi-row inserts (16x throughput). The failure table belongs in our ops runbook: pool exhaustion and index bloat are the two things that will actually break, in that order.
