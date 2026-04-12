# KB Log — Chronological Record

Append-only log of all knowledge-base operations. Format per Karpathy pattern:

```
## [YYYY-MM-DD HH:MM] <op> | <subject> | <metadata>
```

Ops: `ingest`, `compile`, `discover`, `query`, `lint`, `migrate`

Tail with: `grep "^## \[" log.md | tail -20`

---

## [2026-04-12 14:30] migrate | added log.md + CLAUDE.md schema | aligned to Karpathy LLM Wiki pattern

Created `knowledge-base/CLAUDE.md` (schema file defining 3-layer architecture + ops + page conventions + categories).

Created `knowledge-base/log.md` (this file). All future KB operations append here.

Tightened `sources.yaml` to AgentNexLiFy core categories (competitors, ai-llm focused on Claude/agents, verticals we sell to, small-biz SaaS, technical infra we use, relevant regulations, widget/GEO growth).

Scheduled `scripts/daily/kb-autopopulate.sh` via cron for 6am + 6pm daily.

## [2026-04-12 18:30] discover+compile | first-cron-run | raw=+8 wiki=+2 errors=0

First real run of `scripts/daily/kb-autopopulate.sh`. Fired manually (cron next at 6am).

- **Discover** — fetched 14 raw articles across 7 categories via agent-browser
- **Relevance filter** — 6 off-topic rejected manually after run (P.LEAGUE sports, 340B drug pricing, MIT general AI news, Front Porch Forum). URLs stay in `known-urls.json` to prevent refetch. Discover prompt now has explicit relevance filter + list of bad patterns.
- **Compile** — 2/14 completed (both GoHighLevel articles). Context cap reached. Compile prompt now has 4-entry-per-run cap with remainder left in PENDING for next cron.
- **Embeddings** — Supabase kb_articles insert status unverified this run; compile prompt now accepts `embedding_errors=N` as non-fatal so compile continues even if MCP unreachable.
- **INDEX.md** — updated manually to reflect 2 new wiki entries (compile didn't auto-update this run).

**Remaining PENDING (8 entries):** 2 Anthropic pages, 2 pgvector refs, 2 HIPAA pages. Will process at next cron fires (6am + 6pm daily).

## [2026-04-12 19:00] compile | headless-cron-batch-2 | compiled=4 embeddings=0 errors=4

Processed 4 of 6 pending entries this run (4-entry cap). Remaining: 2 HIPAA pages + 4 entries ingested at 22:54:23Z (Claude Opus 4.6, Sonnet 4.6, GHL AI responder, GHL email report).

- **Compiled:**
  - `wiki/ai-llm/anthropic-mission-and-latest-releases.md` (from raw/ai-llm/home-anthropic.md)
  - `wiki/ai-llm/anthropic-careers-and-culture.md` (from raw/ai-llm/careers-anthropic.md)
  - `wiki/technical/pgvector-postgres-vector-search.md` (from raw/technical/github---pgvector-pgvector-*.md)
  - `wiki/technical/pgvector-implementation-guide.md` (from raw/technical/pgvector---geeksforgeeks.md)
- **INDEX.md** — updated with 4 new entries, total 10 articles; added Technical Patterns section population (was empty).
- **Embeddings** — Supabase MCP returned Unauthorized (no SUPABASE_ACCESS_TOKEN in cron env). All 4 embeddings skipped. `kb_articles` table NOT updated this run. Follow-up: populate embeddings once MCP auth wired into cron environment, or run `/kb-compile --embed-only` interactively.
- **Cross-references** — all 4 articles cite ≥1 existing wiki page via `[[slug]]` inline; two pgvector articles cross-link each other for strategic/tactical split.

## [2026-04-12 19:00] discover+compile | cron 18:00 | commits=3 raw=4 wiki=4
