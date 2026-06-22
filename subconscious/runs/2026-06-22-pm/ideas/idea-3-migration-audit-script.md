### Idea 3: Create scripts/check_migration_coverage.py — Object-Level Migration Audit

**Evidence:**
- `docs/dev-knowledge/migration-triage-2026-06-22.md` explicitly recommends this:
  "Stop triaging by file number. Add a deterministic object-existence audit."
- GH #263 "24 pending migrations" alarm is a chronic false positive — naive numeric diff
  includes 001-024 (pre-tracking) + dozens applied under non-numeric names.
- GH #329 ("apply migration 154") was opened despite 154 being already applied.
- 155+ migration files — no current tool to verify coverage accurately.
- Two engineer-hours wasted on the Jun-22 triage audit that could have been automated.

**Action:**
Create `scripts/check_migration_coverage.py`:
- Parse each `migrations/NNN_*.sql` for `CREATE TABLE` / `ADD COLUMN` / `CREATE INDEX` targets
- Query `information_schema` on configured Supabase project via MCP
- Output: list of migrations whose objects genuinely do not exist in live DB

**Impact:**
- Eliminates recurring false-alarm panic on migration counts
- Makes GH issues (#263, #329) self-resolving: run script, get authoritative answer
- Estimated ~2h implementation (schema parsing + Supabase query)

**Category:** operational
