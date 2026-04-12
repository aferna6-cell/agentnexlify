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
