---
type: source
source_id: connector-supabase-schema
origin: connector
connector: Supabase
account: VoltOps
project: pxserpybmajixqrmzaly
accessed: 2026-06-22
sensitivity: normal
tags: [source, connector]
---

# Source: Supabase schema (smoke pass)

## What this is
Read-only `list_tables` on the ACTIVE project `aferna6-cell's Project`
(`pxserpybmajixqrmzaly`) under org [[VoltOps]], 2026-06-22.

## What it proves
- ~130 tables, **RLS enabled on every table** (confirms multi-tenant + RLS invariant).
- Live data volumes: 12 tenants, 2 clients, 27 leads, 1051 conversations, 2706 chat_messages,
  92 faq_entries, 9 appointments, 9 invoices, 18 pipeline_stages.
- **Agent OS is live in prod**: `os_threads` (17), `os_messages` (77), `os_agent_runs` (14),
  `os_memory_entries` (14, voyage-3-lite 512d), `os_graph_nodes` (9) + `os_graph_edges` (1)
  → graph memory shipped (confirms [[Agent OS Graph Memory]]).
- `idempotency_keys` table present (6 rows; 7-day TTL) — the webhook dedup store behind #308.
- This is the canonical [[AgentNexLiFy Platform]] database.

## Note
Table/row counts are operational metadata, not customer PII. No row contents were read.
