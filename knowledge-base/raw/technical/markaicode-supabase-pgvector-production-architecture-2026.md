---
source_url: https://markaicode.com/architecture/vector-database-architecture-with-supabase/
fetched_at: 2026-07-23T00:00:00Z
category: technical
---

# Supabase Vector Database Architecture: Production Best Practices [2026]

**Published:** May 11, 2026 | **Read Time:** 10 minutes | **Author:** Mark

## Executive Summary

"The most failed architectural choice is storing embeddings in the same Postgres instance as your transactional data without isolation." Recommended production setup: dedicated Postgres instance for embeddings with connection pooling, read replicas, and async indexing to prevent write contention.

## Core Architecture Components

Layers: AI Client (LangChain) → API Gateway (Kong) → Supabase Auth + REST → PgBouncer (transaction-mode pooler) → PostgreSQL Primary with pgvector → Read Replicas; Async Queue (Redis) with Indexing Workers.

**Search path:** app generates embedding (`text-embedding-3-small`) → request through Supabase API → PgBouncer assigns idle connection → query hits read replica → pgvector ANN search via HNSW → results with similarity score + metadata.

**Insertion path:** embedding generation offloaded to async queue → worker batches inserts into primary → HNSW index rebuilt on schedule.

## Pgvector Configuration & Index Types

### HNSW vs IVFFlat
- **HNSW**: recommended for sub-10ms p95 on >10M vectors. "HNSW index on 10M vectors achieves p95 latency of 8ms at 100 qps, compared to 45ms for IVFFlat with 4096 lists." Memory ~8x vector size in RAM.
- **IVFFlat**: cost-sensitive option for <1M vectors, lower memory footprint, relaxed latency.

### Production Schema

```sql
CREATE TABLE embeddings (
    id bigserial PRIMARY KEY,
    source_id text NOT NULL,
    embedding vector(768),
    metadata jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX hnsw_idx ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);
```

Parameters: `m = 16` balances build time vs accuracy; `ef_construction = 200` controls construction accuracy; `vector_cosine_ops` standard for text embeddings; tested at 768 dims. Example execution time: 2.31 ms for top-10 index scan.

## Connection Pooling with PgBouncer

```ini
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
min_pool_size = 5
server_idle_timeout = 600
```

"Using transaction pooling, we sustained 500 concurrent search queries with only 20 database connections, cutting Postgres CPU utilization by half." Verify with `SHOW POOLS;`.

## Async Indexing & Batching

BullMQ v5.2.0; accumulate 1000 jobs before flushing to a multi-row INSERT.
- Batching: 5000 embeddings/sec vs single inserts: 300 embeddings/sec
- "Processed batch of 1000 embeddings in 120ms"
- Reduces round trips and index fragmentation during heavy writes.

## RAM & Resource Sizing

| Scale | Instance Type | RAM | Cost/Month |
|-------|--------------|-----|-----------|
| <1M vectors | t3.medium | 4 GB | ~$25 |
| 10M vectors | m6i.large | 8 GB | ~$450 |
| 100M vectors | r6i.2xlarge | 64 GB | ~$3,200 |

Rule: allocate 16 GB RAM per 10M vectors for HNSW headroom. OOM mitigation: use IVFFlat in memory-limited environments.

## Scaling Playbook

| Traffic Tier | Configuration | p95 Latency |
|--------------|---------------|------------|
| Low (<10 qps, <1M vectors) | 1 primary, 0 replicas | 25ms |
| Medium (100 qps, 10M vectors) | 1 primary, 3 read replicas | 12ms |
| High (1000 qps, 100M vectors) | 1 primary, 10 read replicas, sharded | 8ms |

Partition embeddings table by `created_at` or `tenant_id` to reduce index size per replica. Supabase managed Postgres supports up to 40 read replicas (enterprise plan).

## Failure Modes & Detection

| Failure | Root Cause | Detection | Mitigation |
|---------|-----------|-----------|-----------|
| Index bloat | Frequent inserts without maintenance | `pgstattuple('hnsw_idx')` >30% dead tuples | Schedule `REINDEX` during low traffic |
| Connection exhaustion | Too many clients without pooling | PgBouncer rejects at max_client_conn | Increase pool, add replicas, circuit breaker |
| Embedding drift | Model update changes vector distribution | Recall drops, p95 rises | Validate with cosine benchmarks; regenerate |
| Replication lag >5s | Heavy batch insert on primary | `pg_stat_replication` | Increase `wal_keep_size`; sync replication |
| OOM | HNSW consumes 8x vector size in RAM | OOMKilled pods | IVFFlat; 16 GB per 10M vectors |

## RLS with Vectors (multi-tenant)

```sql
CREATE POLICY user_isolation
  ON embeddings
  USING (metadata->>'user_id' = current_user_id());
```

## Security Checklist

RLS on embeddings; VPC/PrivateLink; AES-256 encryption at rest; network policies; rotate Supabase anon + service role keys every 90 days via CI/CD; `pgaudit` streamed to SIEM; per-user connection limits.

## Monitoring & Latency Budget

Track p50/p95 query latency, index build times, pool utilization, dead tuple %, replication lag. Latency budget (p50): embedding generation 150ms (bulk of budget), DB search + pooling 11ms, network ~2ms.

## Operational Experience

6 months in production on AWS RDS db.r6g.large, 10M vectors at 500 qps. Failures: (1) connection pool exhaustion under a marketing-campaign traffic spike — fixed with PgBouncer + read replicas within an hour; (2) index bloat causing query timeouts from missing `REINDEX` — now nightly at 2 AM with 10-minute downtime window.

## Cost Comparison: Supabase pgvector vs Pinecone

- Supabase Pro: $25/month (8 GB RAM, 16 GB disk); 10M vectors ≈ 1.5 GB storage + overhead
- Pinecone starter (1M vectors): $70/month
- Supabase cheaper at moderate traffic but requires Postgres tuning investment. For >100M vectors or strict latency SLAs, purpose-built vector DBs may justify premium.

## Test Specs

AWS G4dn.xlarge, PostgreSQL 15, pgvector 0.7.4, 10M 768-dim vectors, 100 qps baseline / 500 qps production test.
