---
name: schema-guard
description: "Load BEFORE writing queries against Supabase leads/conversations tables in backend/routers/ or authoring migrations/NNN_*.sql. Catches client_id/status/areas_of_interest schema mismatches."
version: 1.1.0
origin: claude
dependencies: python>=3.11
triggers: ["schema guard", "check schema", "database query", "pydantic model", "schema mismatch", "RLS policy", "leads table"]
effort: high
---

# Schema Guard

## When to Use
- Before writing any SQL query
- Before creating or modifying a Pydantic model that maps to a DB table
- Before writing a migration
- Before adding a foreign key reference
- When you see a 422 error on an API endpoint
- When lead capture, appointments, or any data write silently fails

## When NOT to Use
- Frontend-only changes with no database interaction
- Reading data from non-database sources (files, APIs, environment variables)
- When the schema is already verified and you're only doing read-only queries on well-known tables

## Workflow

### Step 1: Check Live Schema
Check the most recent migration files in migrations/ and cross-reference with docs/dev-knowledge/schema-log.md to determine the current schema for the table you're working with.

### Step 2: Cross-Reference Code
Compare the actual schema against:
1. The Pydantic model in the backend routers or models
2. Any SQL queries in the relevant router file
3. The frontend component that displays this data

### Step 3: Gotchas
Schema-mismatch pitfalls that have already caused production bugs:

| Code Says | DB Actually Has | Impact |
|-----------|----------------|--------|
| tenant_id (in leads query) | client_id | Lead capture silently fails |
| lead_stage | status | Lead pipeline breaks |
| password_hash (assumed) | May not be migrated | Auth breaks |
| owner_name (assumed) | May not be migrated | Registration fails |
| FK → old table | Table renamed | Insert fails with FK violation |
| enable_ai_fallback (in Pydantic model) | Exists in widget_configs (migration 101) | Existed in DB but was missing from WidgetConfigUpdateRequest + WidgetConfigDetail — dashboard toggle silently dropped value on save for months |
| enable_structured_lead_parser (in Pydantic model) | Exists in widget_configs (migration 103) | Same class of bug — add new bool DB columns to BOTH update model AND response model |

**IMPORTANT:** The leads table uses `client_id` (NOT `tenant_id`) and `status` (NOT `lead_stage`). Most other tables use `tenant_id`.

**IMPORTANT — Pydantic boolean field sync:** When a new boolean column is added to a table via migration, it must be added to ALL relevant Pydantic models:
1. The response model (`WidgetConfigDetail`, etc.) — so the frontend loads the correct value
2. The update request model (`WidgetConfigUpdateRequest`, etc.) — so the frontend can save it

Missing from either = silent failure. If only missing from (2), the column is readable but can never be written via the API. If missing from both, the column exists in DB but the dashboard has no access to it.

### Step 3.5: Verify RLS Policies

If the table has RLS enabled, verify that policies actually exist. RLS enabled + no policies = all anon/non-service-role INSERTs silently fail (zero rows inserted, no error).

```sql
-- Check if RLS is enabled
SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'TABLE_NAME';

-- Check what policies exist
SELECT tablename, policyname, cmd, roles FROM pg_policies WHERE tablename = 'TABLE_NAME';
```

If RLS is enabled but no policies exist for the relevant roles (anon, authenticated, service_role), either:
1. Add appropriate RLS policies via migration
2. Or ensure the code uses the service_role key for writes

**This is the #1 silent failure class.** The MTOptions audit found 120 of 146 sessions silently failing due to this exact pattern.

### Step 4: Validate Before Committing
Before finalizing any database-touching code:
- [ ] Every column name in code matches the actual DB column name exactly
- [ ] Data types match (especially JSONB fields)
- [ ] Nullable columns are handled
- [ ] Foreign keys point to tables/columns that actually exist
- [ ] If adding a column, a migration file exists
- [ ] leads table uses `client_id`, all other tables use `tenant_id`

### Step 5: Document Changes
If you changed the schema or fixed a mismatch, append to:
- docs/dev-knowledge/schema-log.md
- docs/dev-knowledge/bug-patterns.md (if this was a bug fix)
