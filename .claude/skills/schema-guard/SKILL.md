---
name: schema-guard
description: "Use this skill BEFORE writing any database query, migration, or Pydantic model that touches the database. Prevents schema mismatch bugs — the most common bug class in this repo."
---

# Schema Guard

## When to Use
- Before writing any SQL query
- Before creating or modifying a Pydantic model that maps to a DB table
- Before writing a migration
- Before adding a foreign key reference
- When you see a 422 error on an API endpoint
- When lead capture, appointments, or any data write silently fails

## Workflow

### Step 1: Check Live Schema
Check the most recent migration files in migrations/ and cross-reference with docs/dev-knowledge/schema-log.md to determine the current schema for the table you're working with.

### Step 2: Cross-Reference Code
Compare the actual schema against:
1. The Pydantic model in the backend routers or models
2. Any SQL queries in the relevant router file
3. The frontend component that displays this data

### Step 3: Known Mismatch Patterns
Watch for these — they've all caused production bugs before:

| Code Says | DB Actually Has | Impact |
|-----------|----------------|--------|
| tenant_id (in leads query) | client_id | Lead capture silently fails |
| lead_stage | status | Lead pipeline breaks |
| password_hash (assumed) | May not be migrated | Auth breaks |
| owner_name (assumed) | May not be migrated | Registration fails |
| FK → old table | Table renamed | Insert fails with FK violation |

**IMPORTANT:** The leads table uses `client_id` (NOT `tenant_id`) and `status` (NOT `lead_stage`). Most other tables use `tenant_id`.

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
