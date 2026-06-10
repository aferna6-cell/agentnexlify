# Restore Drill — 2026-06-10 (rubric 6.1)

## What was verified today (logical restore mechanics)

Performed live against project `pxserpybmajixqrmzaly` via Supabase MCP:

1. Created scratch schema `restore_drill`.
2. Copied 4 critical tables (`tenants`, `leads`, `appointments`, `chat_messages`) with `CREATE TABLE ... AS SELECT`.
3. Verified row counts match source exactly: tenants 7/7, leads 25/25, appointments 0/0, chat_messages 2282/2282.
4. Dropped the scratch schema; confirmed zero leftovers.

This proves the data is mechanically exportable and re-importable inside Postgres and that nobody needs schema archaeology to do it. It does NOT yet verify Supabase's own daily backup artifact.

## What still closes 6.1 fully (10-minute dashboard step, owner/partner)

Supabase's managed backups can only be restore-tested from the dashboard:

1. supabase.com/dashboard → project `pxserpybmajixqrmzaly` → Database → Backups.
2. Confirm a daily backup exists with a recent timestamp (screenshot it).
3. **Do NOT restore over production.** Use "Restore to a new project" (or download the backup if on a plan tier that allows it).
4. In the restored copy, run the verification query below and compare to production counts taken the same day.
5. Delete the restored scratch project afterward (it bills hourly).

```sql
SELECT
  (SELECT count(*) FROM tenants)       AS tenants,
  (SELECT count(*) FROM leads)         AS leads,
  (SELECT count(*) FROM chat_messages) AS chat_messages;
```

6. Record date + counts here; flip rubric 6.1 to 2.

## Cadence

Re-run the dashboard drill quarterly and after any Supabase plan/instance change. Re-run the logical drill (steps above, all via MCP `execute_sql`) any time — it's free and takes two minutes.
