---
type: procedure
name: "Database Migration Workflow"
tags:
  - procedure
  - schema
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Database Migration Workflow

## When to use
Any schema change. No ad-hoc SQL.

## Steps
1. Create the next numbered file `migrations/NNN_name.sql` (zero-padded, sequential).
2. Apply via the Supabase MCP (`apply_migration`).
3. Update `docs/dev-knowledge/schema-log.md`.
4. Flag the migration in the commit message.
5. Respect [[client_id vs tenant_id]] and never leave a half-done migration.

## Notes
- No ORM (see [[FastAPI without ORM]]); migrations are the only schema mechanism.
- Deploy order applies migrations **first** — see [[Production Deploy]].

## Related
- [[FastAPI without ORM]] · [[client_id vs tenant_id]] · [[Production Deploy]]

## Provenance
- [[repo-agentnexlify-claude-md]] · [[repo-agentnexlify-agents-md]]
