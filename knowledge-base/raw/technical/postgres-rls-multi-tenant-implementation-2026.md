---
title: Row-Level Security in PostgreSQL — Multi-Tenant Implementation
date: 2026-01-25
source_url: https://oneuptime.com/blog/post/2026-01-25-row-level-security-postgresql/view
fetched_at: 2026-08-25
category: technical
tags: [postgres, rls, multi-tenant, security, supabase, policies]
---

# Row-Level Security in PostgreSQL: Multi-Tenant Implementation

**Published:** January 25, 2026

## The Problem RLS Solves

In a shared-schema multi-tenant application, every query must be filtered by tenant. Enforcing that in application code means every developer, on every query, forever, must remember the `WHERE tenant_id = ...` clause. One forgotten clause is a cross-tenant data leak.

Row-Level Security moves that filter into the database, where it cannot be forgotten.

## Enabling RLS

```sql
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads FORCE ROW LEVEL SECURITY;
```

`ENABLE` applies policies to normal users but **exempts the table owner**. `FORCE` applies them to the owner too. In practice, forgetting `FORCE` is the most common reason a policy silently does nothing during testing — the connection is running as owner.

## Setting Tenant Context

Two mechanisms, with different tradeoffs.

### Session variables

```sql
SET app.current_tenant = '11111111-1111-1111-1111-111111111111';
```

```sql
CREATE POLICY tenant_isolation ON leads
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

Use `set_config(..., true)` for transaction-local scope so the value does not leak across pooled connections:

```sql
SELECT set_config('app.current_tenant', $1, true);
```

Use `current_setting('app.current_tenant', true)` (with the missing_ok flag) to return NULL instead of erroring when unset — then policies fail closed rather than throwing.

### JWT claims (Supabase pattern)

```sql
CREATE POLICY tenant_isolation ON leads
  USING (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);
```

The claim is signed and cannot be spoofed by the client. This is the preferred pattern where an auth layer already issues JWTs.

## Policy Types

Separate policies per command give precise control:

```sql
CREATE POLICY leads_select ON leads FOR SELECT
  USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY leads_insert ON leads FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY leads_update ON leads FOR UPDATE
  USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY leads_delete ON leads FOR DELETE
  USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
```

**`USING` filters which existing rows are visible. `WITH CHECK` validates rows being written.** An UPDATE policy with only `USING` lets a tenant move a row to another tenant by changing the tenant column — a real escalation path.

## Connection Pooling Pitfalls

The dominant source of production RLS bugs. With PgBouncer in transaction mode, a session-level `SET` can persist onto a connection reused by a different tenant.

Rules:

1. Use `set_config(key, value, true)` — the `true` makes it transaction-scoped
2. Set the tenant context **inside the same transaction** as the queries
3. Never rely on session-level `SET` behind a transaction pooler
4. Reset context explicitly if using session pooling

```python
async with pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute("SELECT set_config('app.current_tenant', $1, true)", tenant_id)
        rows = await conn.fetch("SELECT * FROM leads")
```

## Performance

RLS predicates are appended to every query, so they must be indexable.

- **Index the tenant column** — a policy on an unindexed column forces a sequential scan on every query
- **Put the tenant column first in composite indexes**: `CREATE INDEX ON leads (tenant_id, created_at DESC)`
- **Avoid function calls in policies** that the planner cannot inline; `current_setting()` is STABLE and inlines acceptably, but a policy calling a VOLATILE function per row is a performance cliff
- **Watch subqueries in policies** — a policy containing `IN (SELECT ...)` executes per row in some plans. Prefer a direct column comparison
- Verify with `EXPLAIN ANALYZE` that the tenant predicate produces an index scan

Well-designed RLS typically costs single-digit percentage overhead. Badly designed RLS can be 10x.

## BYPASSRLS and Service Roles

Background jobs, migrations, and admin tooling need to cross tenants:

```sql
CREATE ROLE service_role WITH LOGIN BYPASSRLS;
```

Treat `BYPASSRLS` credentials as the crown jewels — they nullify every policy. Never use the service role for request-path queries. In Supabase terms: the service key belongs on the server and never in the browser.

## Testing RLS

Policies are security controls and deserve tests that attempt violations:

```sql
BEGIN;
SELECT set_config('app.current_tenant', 'tenant-a-uuid', true);
-- expect: only tenant A rows
SELECT count(*) FROM leads;
-- expect: 0 rows affected, not an error
UPDATE leads SET status = 'x' WHERE tenant_id = 'tenant-b-uuid';
ROLLBACK;
```

Test matrix that catches real bugs:

1. Tenant A cannot SELECT tenant B rows
2. Tenant A cannot UPDATE tenant B rows
3. Tenant A cannot INSERT a row with tenant B's ID
4. Tenant A cannot UPDATE its own row to tenant B's ID (the `WITH CHECK` case)
5. Unset context returns zero rows rather than all rows
6. New tables have RLS enabled (assert against `pg_class.relrowsecurity`)

A CI check that fails when any table in the tenant schema lacks RLS prevents the most dangerous regression: a new table shipped without a policy.

## Migration Strategy for an Existing App

1. Add the tenant column and backfill
2. Add indexes on the tenant column
3. Create policies but leave RLS disabled
4. Enable RLS on a staging copy and run the full test suite
5. Enable per table in production, monitoring for empty result sets (the signature of missing context)
6. Add `FORCE` once the application no longer connects as owner
7. Remove now-redundant application-level tenant filters last, not first

Keeping application-level filters during rollout means a policy misconfiguration degrades to redundant filtering rather than a leak.

## Defense in Depth

RLS is one layer, not the whole answer. Combine with:

- Application-level tenant scoping (belt and suspenders during and after migration)
- Least-privilege database roles per service
- Separate credentials for request path vs background jobs
- Audit logging on sensitive tables
- Regular verification that every tenant-scoped table has RLS enabled
