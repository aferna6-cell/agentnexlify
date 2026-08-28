---
title: Row Level Security for Tenants in Postgres (Crunchy Data)
date: 2024-04-03
source_url: https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres
fetched_at: 2026-08-25
category: technical
tags: [postgres, rls, multi-tenant, session-variables, policies, crunchy-data]
---

# Row Level Security for Tenants in Postgres

**Crunchy Data · April 3, 2024**

## Setup

A single shared table holding rows for many tenants:

```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    name TEXT NOT NULL,
    balance NUMERIC
);

INSERT INTO accounts (tenant_id, name, balance) VALUES
    (1, 'Acme Corp', 1000),
    (1, 'Acme Sub',   500),
    (2, 'Globex',    2500);
```

Enable RLS:

```sql
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
```

Once enabled with no policy defined, the table returns **zero rows** to non-owner roles. RLS defaults to deny — a useful property, because a table you forget to write a policy for fails closed.

## The Session-Variable Pattern

Postgres allows arbitrary namespaced runtime settings. Use one to carry the current tenant:

```sql
SET app.current_tenant = '1';
SELECT current_setting('app.current_tenant');
```

Define the policy against it:

```sql
CREATE POLICY tenant_isolation_policy ON accounts
    USING (tenant_id = current_setting('app.current_tenant')::INT);
```

Now:

```sql
SET app.current_tenant = '1';
SELECT * FROM accounts;   -- Acme rows only

SET app.current_tenant = '2';
SELECT * FROM accounts;   -- Globex only
```

The application never writes a tenant predicate. The database applies it.

## Table Owners Bypass Policies

A critical gotcha: RLS policies do **not** apply to the table owner by default. Testing as the owner shows all rows and creates false confidence that the policy is broken (or worse, that it works when it does not).

```sql
ALTER TABLE accounts FORCE ROW LEVEL SECURITY;
```

`FORCE` makes policies apply to the owner as well. Alternatively — and preferably — connect the application as a dedicated non-owner role.

```sql
CREATE ROLE app_user LOGIN PASSWORD '...';
GRANT SELECT, INSERT, UPDATE, DELETE ON accounts TO app_user;
```

## Guarding Writes With WITH CHECK

`USING` governs visibility of existing rows. It does not govern what may be written. Without `WITH CHECK`, a tenant can insert or update rows carrying another tenant's ID:

```sql
CREATE POLICY tenant_isolation_policy ON accounts
    USING (tenant_id = current_setting('app.current_tenant')::INT)
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::INT);
```

With `WITH CHECK` in place, an attempt to write a foreign tenant_id raises:

```
ERROR:  new row violates row-level security policy for table "accounts"
```

## Handling an Unset Variable

If `app.current_tenant` is never set, `current_setting()` raises an error:

```
ERROR:  unrecognized configuration parameter "app.current_tenant"
```

Pass the `missing_ok` argument to get NULL instead:

```sql
CREATE POLICY tenant_isolation_policy ON accounts
    USING (tenant_id = current_setting('app.current_tenant', true)::INT);
```

A NULL comparison yields NULL, which the policy treats as false — so an unset context returns zero rows rather than erroring or, far worse, returning everything.

## Transaction-Scoped Context and Pooling

`SET` persists for the life of the session. Behind a connection pooler, a session may be handed to a different tenant's request with a stale value still set. Use the transaction-local form:

```sql
BEGIN;
SELECT set_config('app.current_tenant', '1', true);
SELECT * FROM accounts;
COMMIT;
```

The third argument `true` means "local to the current transaction" — the value is discarded on COMMIT or ROLLBACK, so it cannot leak onto the next borrower of that connection.

## Indexing

The policy predicate is appended to every query against the table. Index the tenant column, and lead composite indexes with it:

```sql
CREATE INDEX ON accounts (tenant_id);
CREATE INDEX ON accounts (tenant_id, created_at DESC);
```

Confirm with `EXPLAIN` that the plan uses an index scan rather than a sequential scan with a filter.

## Multiple Policies

Multiple permissive policies on the same table are combined with OR. This is how you grant an admin role broader visibility without dropping tenant isolation for everyone else:

```sql
CREATE POLICY admin_all ON accounts
    TO admin_role
    USING (true);
```

For AND semantics, declare a policy `AS RESTRICTIVE`.

## Summary

- RLS defaults to deny — no policy means no rows
- `ENABLE` exempts the owner; `FORCE` does not
- `USING` controls reads; `WITH CHECK` controls writes — you need both
- `current_setting(key, true)` fails closed on unset context
- `set_config(key, value, true)` is the pooler-safe way to set context
- Index the tenant column or pay for it on every query
