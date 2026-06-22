---
type: topic
name: "client_id vs tenant_id"
tags:
  - topic
  - schema
  - invariant
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# client_id vs tenant_id

## The invariant
On the `leads` and `conversations` tables the tenant foreign key is **`client_id`**, not
`tenant_id`. Other tables use `tenant_id`. Confusing the two has shipped 3+ production bugs;
the `client_id` fix landed in migration 076, canonical baseline migration #106.

## Why it matters
- It is the single most-repeated schema invariant in the repo (CLAUDE.md critical rule #1).
- Related column invariants: lead status column is `status` (not `lead_stage`); service
  interest column is `areas_of_interest` (not `service_interest`).

## Related
- [[Multi-Tenant Architecture]] · [[Database Migration Workflow]] · [[User Engineering Rules]]

## Provenance
- [[dev-knowledge-canonical-schema]] · [[repo-agentnexlify-claude-md]]
