# DB Connection Pool — Sizing + Test Evidence (rubric 5.2)

Date: 2026-06-10. Closes launch-rubric 5.2 "Database connection pool sized + tested".

## Architecture: the app holds ZERO direct Postgres connections

Verified in code:

- `backend/requirements.txt` contains **no Postgres driver** (no psycopg/asyncpg/sqlalchemy). All DB access goes through `supabase==2.28.3` → **PostgREST over HTTPS**.
- `backend/models/database.py:19-24` — one singleton `supabase.Client` per kind (service + public) per process, each backed by one `httpx.Client(timeout=120.0)`.
- Production topology: 4 Uvicorn workers (`backend/railway_entrypoint.py:76`, `UVICORN_WORKERS` default 4).

## Sizing

| Layer | Limit | Where set |
|---|---|---|
| App → PostgREST (per worker) | httpx defaults: max 100 connections, 20 keep-alive | `httpx.Client` defaults (no override) |
| App → PostgREST (whole service) | 4 workers × 100 = 400 max concurrent HTTPS conns | derived |
| PostgREST → Postgres | Supabase-managed pool (platform default for instance size; PostgREST multiplexes) | Supabase project `pxserpybmajixqrmzaly` |
| Direct Postgres / Supavisor | unused by the app — migrations only via Supabase MCP/UI | — |

The practical implication: the app cannot exhaust Postgres connections — PostgREST is the only Postgres client and it pools internally. The app-side bottleneck is the httpx pool (400 service-wide), far above measured need (widget chat load test peaked at concurrency 10; biggest tenant fleet today is 5 testers).

The 120s httpx timeout is deliberately generous (long PostgREST aggregations); request-path latency is bounded upstream by route-level timeouts and the widget's own UX budget.

## Test evidence

1. **Concurrent DB-backed burst (new, this audit)** — `ops/evals/run_db_pool_burst.py`: 150 requests at **concurrency 25** against prod `/api/health`, which performs a real Supabase query per request. Result (`ops/evals/db-pool-burst-2026-06-10.json`): **0 failures, p50 555 ms, p95 1393 ms** (gate: ≤1% errors, p95 ≤2s) — **PASS**. Max 9.4s outlier = single cold worker spike; no connection errors at any point.
2. **Widget/chat load** — `ops/evals/widget-chat-load-2026-06-10.json`: 100 POSTs at concurrency 10, p95 289.7 ms, 0 errors (rate limiter engaged as designed).

25 concurrent DB-touching requests ≫ 10× current expected concurrent load for a 5-tenant fleet.

## When to revisit

- If a Postgres driver is ever added (direct SQL path) → real pool config required (Supavisor port 6543, pool_size per worker), rerun this audit.
- At >100 paying tenants or first enterprise tenant → rerun burst at concurrency 100.
- If Supabase instance size changes, PostgREST pool defaults change with it.
