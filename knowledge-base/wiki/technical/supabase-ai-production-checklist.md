---
title: "Supabase AI Production Checklist — pgvector Indexing, HNSW Tuning, and Scale Prep"
category: technical
tags: ["supabase", "pgvector", "hnsw", "ivfflat", "production-readiness", "vector-search", "ann"]
sources: ["raw/technical/going-to-prod.md"]
created: 2026-04-20
updated: 2026-04-20
summary: "Supabase's AI production guide frames the pgvector tradeoff as accuracy vs. RAM vs. QPS; HNSW is preferred, ef_construction ≥ 2×m, pre-warm via pg_prewarm and 10k+ warm-up queries before prod cutover."
---

# Supabase AI Production Checklist — pgvector Indexing, HNSW Tuning, and Scale Prep

Supabase's production guide for AI applications is the narrow but critical reference for taking a pgvector-backed knowledge base from prototype to production traffic. The core tradeoff is explicit: exact KNN sequential scans deliver 100% accuracy but scale poorly; ANN indexes (HNSW or IVFFlat) deliver low-latency high-QPS search at the cost of approximation and RAM. For AgentNexLiFy's KB (47+ wiki articles today, compiled with Voyage AI voyage-3-lite 512-dim embeddings per [[pgvector-postgres-vector-search]]), the dataset is small enough that sequential scans still work, but the guide maps the path forward as tenant KBs grow into thousands of articles per client.

The index-or-not decision hinges on three factors: dataset size, query volume, and accuracy floor. Small datasets with low QPS and 100% accuracy requirements can skip indexes entirely — sequential scans aren't RAM-bound and don't need tuning. Above that threshold, HNSW is the recommended index type over IVFFlat because of better raw performance at 1536 dimensions and robustness to changing data (new inserts don't require index rebuilds the way IVFFlat benefits from). The accuracy cost of moving to ANN is real — you're replacing KNN with approximate search — but properly-tuned HNSW routinely hits >95% recall, which is indistinguishable from exact search for most retrieval workloads. See [[encore-pgvector-guide-2026]] for the production-latency story that makes this tradeoff easy: LLM generation dominates the request budget at 500ms-3s, so ANN's 20ms vs. sequential scan's 200ms is invisible.

HNSW has three tuning knobs. `m` (bi-directional links per element, default 16, range 12–48) governs graph connectivity; higher m helps high-dimensional or high-accuracy workloads but increases memory. `ef_construction` (dynamic nearest-neighbor list size during build, default 64) controls build-time index quality; must be ≥ 2×m. `ef_search` (same list size during query, default 40) trades query latency for accuracy. The diagnostic: set ef_search = ef_construction and measure accuracy; if below 0.9, raise ef_construction. Supabase's own benchmark on 1M OpenAI embeddings found m=32 / ef_construction=80 delivered 35% higher QPS than m=24 / ef_construction=56 — real, measurable differences from small parameter moves.

IVFFlat's two parameters (`lists` and `probes`) are coupled: higher lists means finer partitioning and better accuracy potential, but only if probes rises to cover enough of them. Higher probes means slower queries but better accuracy. For AgentNexLiFy's workload HNSW is the clear choice — the KB grows incrementally as new raw sources compile into wiki articles, and IVFFlat's centroid-based approach suffers when the data distribution shifts over time.

Pre-warming is not optional for production cutover. Two mechanisms: `pg_prewarm` loads the index into RAM explicitly (`select pg_prewarm('vecs.docs_vec_idx')`), and a 10k–50k warm-up query run populates PostgreSQL's buffer cache with hot pages. Without pre-warming, the first production queries hit cold cache and return latencies 5–10× higher than warm steady-state — the kind of cold-start spike that alerts dashboards and wakes on-call engineers unnecessarily. For distance metrics, prefer inner-product over L2 or cosine when embeddings are normalized (Voyage AI outputs are); Voyage-3-lite's 512-dim normalized vectors fit this pattern.

The production rollout sequence is deliberate: over-provision RAM initially (Supabase recommends 8XL minimum for meaningful workloads), upload data, benchmark with default params, observe actual RAM usage, scale down to the compute tier matching observed RAM, reload data to warm the new instance, re-benchmark with real queries. Only after observing steady-state performance should you tune m and ef_construction upward to chase higher QPS — rebuilding the index each time, iterating on the accuracy-vs-QPS curve. This contrasts with the naive "set m=32 and ship it" approach that leaves performance and cost on the table for workloads that could justify tighter or looser parameters.

## Key Concepts

- **KNN vs ANN** — K-Nearest Neighbors (exact, 100% accurate, sequential scan) vs Approximate Nearest Neighbors (indexed, ~95%+ recall, sub-linear latency). Production vector search almost always means ANN.
- **HNSW (Hierarchical Navigable Small World)** — Graph-based ANN index; each layer skips over more of the data for fast candidate search. Preferred over IVFFlat for dynamic datasets and high-dimensional embeddings.
- **ef_construction / ef_search** — HNSW's build-time and query-time dynamic list sizes. Raising them trades build/query cost for accuracy. Must satisfy ef_construction ≥ 2×m.
- **Pre-warming** — Loading index pages into PostgreSQL's buffer cache before taking production traffic. Uses pg_prewarm plus bulk warm-up queries; prevents cold-start latency spikes on cutover.
- **Recall@k** — Fraction of true top-k nearest neighbors returned by the ANN index. >0.95 is typical production target; below 0.9 signals under-tuned parameters or under-provisioned RAM.

## Related Articles

- [[pgvector-postgres-vector-search]] — Native pgvector primer covering distance metrics and index options; prerequisite context for the tuning covered here.
- [[pgvector-implementation-guide]] — Hands-on install + first-query patterns; complements this production-focused checklist.
- [[encore-pgvector-guide-2026]] — Why the HNSW-vs-sequential tradeoff is often invisible in practice: LLM generation dominates the latency budget.
- [[anthropic-contextual-retrieval]] — Content-side optimization (prepending context to chunks) that compounds with the index-side tuning described here.

## Relevance to AgentNexLiFy

AgentNexLiFy's per-tenant knowledge base architecture means the production-readiness question gets asked once per vertical and then multiplied. Today's 47-article wiki doesn't need an HNSW index — sequential scan is fine — but the per-tenant KB pattern scales linearly with clients. A 500-tenant future state with 100 articles per tenant is 50,000 vectors, squarely in HNSW territory. The concrete actions: (1) add a migration guarded behind a feature flag that creates an HNSW index on `kb_articles.embedding` with m=32 / ef_construction=80 once any tenant exceeds 1,000 articles; (2) document the warm-up procedure (pg_prewarm + 10k query replay) in the deploy-check skill so Railway cutovers don't hit cold caches; (3) track recall@10 as a monitored metric, not a one-time benchmark, because embedding model updates or reranker changes can shift the accuracy curve without touching index code. Voyage-3-lite outputs normalized vectors, so the inner-product distance recommendation applies directly — confirm the index definition uses `vector_ip_ops` rather than `vector_cosine_ops` when the index is added.
