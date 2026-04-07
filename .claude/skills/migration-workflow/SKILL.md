---
name: migration-workflow
description: "Use this skill when creating, applying, or verifying database migrations to prevent migrations that exist as files but are never applied to live Supabase."
version: 1.0.0
origin: claude
triggers: ["database migration", "create migration", "apply migration", "migration checklist", "verify migration", "schema change"]
---

# Migration Workflow

## When to Use
- Creating a new database table or column
- Modifying existing schema
- Before deploying features that depend on schema changes
- During morning/evening reviews when checking migration status

## When NOT to Use
- Writing queries against existing schema without changes (no migration needed)
- Frontend-only changes (no database involvement)
- Non-schema configuration changes (use appropriate config tools)

## Creating a Migration

1. **Find the next number:** Check `migrations/` directory for the highest existing number
2. **Create the file:** `migrations/NNN_descriptive_name.sql`
3. **Include in the SQL:**
   - `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE` (idempotent when possible)
   - Indexes for common query patterns
   - `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
   - RLS policies
   - Comments explaining the purpose
4. **Document immediately:** Add entry to `docs/dev-knowledge/schema-log.md`
5. **Flag in commit message:** Include "Migration NNN" in the commit message

## Applying a Migration

**Migrations do NOT auto-apply.** Each must be manually run:

1. Open the Supabase SQL editor
2. Copy the migration SQL
3. Execute it
4. Verify by querying: `SELECT * FROM new_table LIMIT 1` or `SELECT column_name FROM information_schema.columns WHERE table_name = 'table' AND column_name = 'new_col'`
5. Update schema-log.md with "Applied on YYYY-MM-DD"

## Verification Checklist

Use this when reviewing migration status (morning/evening routines):

```sql
-- Check if a table exists
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'table_name');

-- Check if a column exists
SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'table_name' AND column_name = 'column_name');

-- List all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
```

## Common Mistakes to Avoid

1. **Creating migration file but not applying it** — This is the #1 failure mode. Features ship, schema doesn't exist, runtime errors.
2. **Not documenting in schema-log.md** — Future sessions won't know the migration exists.
3. **Conflicting migration numbers** — Before creating migration NNN, run `ls migrations/NNN*.sql`. If a file exists at that number, use NNN+1. Duplicate migration numbers exist in this repo (005, 007, 066, 067, 068) and cannot be applied twice.
4. **Missing RLS** — Every table needs RLS enabled and a tenant-scoped policy.
5. **Not flagging in commit message** — Makes it hard to track which commits need schema changes.

## CLAUDE.md Table

After creating a new table, add it to the CLAUDE.md schema table:

| Table | Purpose | Key Columns |
|-------|---------|-------------|

Include tenant FK, important columns, and any non-obvious column names.
