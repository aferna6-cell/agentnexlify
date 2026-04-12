---
title: "pgvector Implementation Guide — Build, Enable, Query"
category: technical
tags: ["pgvector", "postgres", "installation", "psycopg2", "hybrid-search", "tutorial"]
sources: ["raw/technical/pgvector---geeksforgeeks.md"]
created: 2026-04-12
updated: 2026-04-12
summary: "Hands-on install and first-query walkthrough for pgvector on a self-managed Postgres, with the Python client pattern that mirrors AgentNexLiFy's Supabase usage."
---

# pgvector Implementation Guide — Build, Enable, Query

This article covers the mechanical steps to install pgvector on a self-managed Postgres, enable the extension, create a vector column, and run similarity queries from both SQL and Python. AgentNexLiFy does not do this work directly — Supabase ships pgvector preinstalled, as described in [[pgvector-postgres-vector-search]] — but the same patterns apply whenever the product runs against a non-Supabase Postgres (local dev without Supabase, a self-hosted tenant POC, or a disaster-recovery replica). The GeeksforGeeks source walks through the full path from OS-level install to Python querying; this article condenses it into the shape AgentNexLiFy engineers actually need.

The install path on Debian/Ubuntu is straightforward: install `postgresql`, `postgresql-contrib`, `postgresql-server-dev-14` (the dev headers that provide `postgres.h`), plus `git`, `make`, `gcc`, and `libpq-dev` for the build. Clone `github.com/pgvector/pgvector`, `make`, `make install`. The `server-dev` package version must match the running Postgres major version — 14 in the source example, 16 on current Supabase. After the install, enable the extension per database: `CREATE EXTENSION IF NOT EXISTS vector;`. This is identical on Supabase (where the extension is already compiled and `CREATE EXTENSION` is the only step) and on a hand-built Postgres.

A working first query looks like this:

```sql
CREATE TABLE documents (
  id SERIAL PRIMARY KEY,
  content TEXT,
  embedding vector(3)
);

INSERT INTO documents (content, embedding) VALUES
  ('AI in healthcare', '[0.11, 0.45, 0.33]'),
  ('Machine learning', '[0.12, 0.44, 0.34]'),
  ('Cooking recipes',  '[0.87, 0.13, 0.55]');

SELECT id, content, embedding <-> '[0.10, 0.46, 0.32]' AS distance
FROM documents
ORDER BY distance
LIMIT 3;
```

The `<->` operator computes L2 (Euclidean) distance; swap to `<=>` for cosine distance if your embedding model outputs normalized vectors (voyage-3-lite, OpenAI text-embedding-3, Cohere embed-english-v3 all fall in this bucket). The three example vectors are synthetic; real embeddings come from an embedding API call that returns a 256/512/1536/3072-dimensional float array. AgentNexLiFy's production pattern uses Voyage's voyage-3-lite at 512 dimensions and cosine distance, stored in `kb_articles.embedding` via `INSERT ... ON CONFLICT (slug) DO UPDATE` for idempotent re-runs.

The Python client pattern uses `psycopg2` plus the `pgvector` package:

```python
import psycopg2
from pgvector.psycopg2 import register_vector

conn = psycopg2.connect(
    "dbname=postgres user=postgres password=password host=localhost port=5432"
)
register_vector(conn)

cur = conn.cursor()
cur.execute(
    "SELECT id, content FROM documents ORDER BY embedding <=> %s LIMIT 5",
    ([0.10, 0.46, 0.32],),
)
print(cur.fetchall())
```

The critical call is `register_vector(conn)`, which tells psycopg2 how to serialize Python lists and numpy arrays into Postgres's `vector` type and how to parse the type back on the way out. Without it, psycopg2 sends the array as text and Postgres rejects it. AgentNexLiFy's backend uses Supabase's Python client rather than raw psycopg2 for most queries, but any code that directly builds vector queries (embedding ingest scripts, batch re-embedding jobs) calls `register_vector` once on connection setup.

Authentication is the one trap in the install flow. Default Postgres on Debian uses peer authentication for local connections, which means only the `postgres` OS user can connect to the `postgres` DB user. The source walks through editing `/etc/postgresql/14/main/pg_hba.conf` to switch `local all postgres peer` to `local all postgres md5`, restarting Postgres, and setting a password. For AgentNexLiFy this is almost never necessary in practice (Supabase handles auth via the service role key and Postgres connection strings include the password directly), but it's the right thing to know when debugging a local dev Postgres that silently refuses connections.

The GeeksforGeeks source also includes a comparison table of pgvector versus FAISS, ChromaDB, and Milvus. The short version: FAISS is a C++ library for in-memory research workloads, ChromaDB is a Python-native local DB for AI prototypes, Milvus is a distributed vector DB for billion-scale enterprise search. pgvector wins on operational simplicity for anything that already has a Postgres — which is AgentNexLiFy's entire stack — and loses only at the billion-vector scale where a dedicated distributed store earns its operational cost. See [[pgvector-postgres-vector-search]] for the strategic argument; this article is the tactical one.

## Key Concepts

- **peer authentication** — Postgres default on Linux where the OS username must match the DB username. Surprises first-time installers by refusing connections that would otherwise look correct.
- **register_vector** — Python-side call from the `pgvector` package that teaches psycopg2 the vector type. Required once per connection before any vector INSERT or ORDER BY query.
- **`postgresql-server-dev-<version>`** — Debian/Ubuntu package providing the C headers (`postgres.h`) that pgvector's build needs. Must match the running Postgres major version or the build fails.
- **Approximate nearest neighbor (ANN)** — Indexed vector search that returns near-optimal results in sublinear time, trading a small recall drop for a large latency win. IVFFlat and HNSW are pgvector's two ANN index types.

## Related Articles

- [[pgvector-postgres-vector-search]] — The strategic/architectural view; this article is the implementation companion.
- [[llm-wiki-karpathy-pattern]] — The knowledge-management pattern pgvector enables inside AgentNexLiFy's Supabase.

## Relevance to AgentNexLiFy

Most AgentNexLiFy engineers will never run `apt-get install postgresql-server-dev-14` — Supabase makes that step irrelevant. The useful takeaways are the Python query pattern (`register_vector` + `%s` parameter binding for the query vector), the operator choice (`<=>` cosine distance for any Voyage or OpenAI embedding), and the awareness that the extension's comparison advantage is operational simplicity, not raw throughput. When evaluating whether to move to a dedicated vector DB in the future, the answer is: only if a single tenant's corpus grows past 10M vectors, which is not on the current roadmap.
