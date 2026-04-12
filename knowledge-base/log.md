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
