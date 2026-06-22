---
type: decision
status: active
tags:
  - decision
  - architecture
source_status: source-backed
confidence: high
---

# Decision: FastAPI + Supabase, no ORM

## Decision
Use FastAPI with the direct Supabase client and raw SQL **numbered migrations**. No
SQLAlchemy/Alembic ORM.

## Rationale
Keep the data layer explicit and simple; migrations are auditable files applied via the
Supabase MCP.

## Consequences
- Schema changes only via `migrations/NNN_name.sql` (see [[Database Migration Workflow]]).
- Common bug class: `dict.get("key", default)` returns `None` on SQL NULL — use
  `dict.get("key") or "default"`. Source: [[eng-memory-lessons-learned]]

## Related
- [[Database Migration Workflow]] · [[client_id vs tenant_id]] · [[AgentNexLiFy Platform]]

## Provenance
- [[dev-knowledge-architecture-decisions]]
