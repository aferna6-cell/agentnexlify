---
name: supabase-postgres-best-practices
description: Postgres performance + schema best practices from Supabase. Load when writing, reviewing, or optimizing Postgres queries, designing tables/indexes in migrations/, reviewing RLS policies, or debugging slow Supabase queries in backend/routers/*.
origin: https://github.com/supabase/agent-skills
version: 1.0.0
triggers:
  - slow supabase query
  - postgres optimization
  - rls policy review
  - index strategy
  - query performance
  - supabase best practices
paths: migrations/**.sql,backend/routers/**.py,backend/services/tenant_scope.py
user-invocable: false
---

# Supabase Postgres Best Practices

## When to Use
- Writing new Supabase queries in `backend/routers/*`
- Designing tables/indexes in a new `migrations/NNN_*.sql`
- Reviewing or adding RLS policies
- Debugging slow queries or connection pool issues

## When NOT to Use
- Simple CRUD against a single well-indexed table
- Non-Supabase datastores (different rule set)
- Migration structure questions (use `migration-workflow`)

## Top 8 rule categories

Prioritized by impact (upstream supabase/agent-skills):

1. **Query performance** — avoid SELECT *; use specific columns. Avoid N+1 via joins or `.select()` nesting. Index WHERE/ORDER BY columns.
2. **Connection management** — use Supabase client singletons (per-worker). Our backend does this via `backend/models/database.py:get_service_supabase()`.
3. **RLS policies** — every tenant-scoped table MUST have RLS ON + a policy. See `.claude/rules/schema-discipline.md`.
4. **Index strategy** — partial indexes for filtered queries, BRIN for timestamp columns, GIN for JSONB.
5. **Transactions** — wrap multi-statement writes in `.rpc()` or explicit transactions. Never split dependent writes.
6. **Upserts over select-then-insert** — `.upsert()` with `on_conflict` avoids race conditions.
7. **Avoid CTEs for filters** — use subqueries unless the CTE is materialized and reused.
8. **Connection pooling** — use pgbouncer on Supabase for serverless; single-session transactions on Railway backend.

## AgentNexLiFy-specific overrides
- `leads` + `conversations` tables use `client_id`, NOT `tenant_id`. See `.claude/rules/schema-discipline.md`.
- `status` NOT `lead_stage`. `areas_of_interest` NOT `service_interest`.
- All schema changes via numbered migration files (`migrations/NNN_name.sql`) applied via `mcp__supabase__apply_migration`.
- Use `tenant_scope.py` helpers (`tenant_select`, `tenant_table`, `tenant_insert`) — handles client_id/tenant_id mapping.

## Full upstream skill
https://github.com/supabase/agent-skills/blob/main/skills/supabase-postgres-best-practices/SKILL.md

Install upstream version for the full 8×rules breakdown with SQL examples:
```
npx skillsadd supabase/agent-skills
```
