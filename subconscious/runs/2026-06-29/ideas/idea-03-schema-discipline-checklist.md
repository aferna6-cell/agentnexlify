# Idea 03 — Add Tenant-Scope Registration Checklist to schema-discipline.md

**Category:** code_health  
**Effort:** XS (~30 min, doc edit only)  
**Moratorium-safe:** YES — AUTONOMOUS-EXECUTABLE, doc-only change  
**AUTONOMOUS-EXECUTABLE:** YES — path-scoped rule file edit, nightly scope  

## Evidence

- 3 confirmed occurrences of `_TENANT_COLUMN_OVERRIDES` miss for new tables (os_graph_nodes, os_graph_edges — run 54 confirmed)
- Parking lot ROI 2.0, added run 54 debate
- `.claude/rules/schema-discipline.md` is path-scoped to `backend/**/*.py` — auto-loads in every backend session
- New Agent OS services continue shipping without tenant-scope registration check

## What It Would Build

Append 5-question "New Table Checklist" to `.claude/rules/schema-discipline.md`:
1. Is there a `client_id` column?
2. Is it in `_TENANT_COLUMN_OVERRIDES` dict?
3. Is there RLS policy on the table?
4. Does every query filter by `client_id`?
5. Is there a migration for the column + index?

## Assessment

Good preventive fix. Low urgency: no new occurrence since run 54 (19 runs ago). No new forcing function this run. Would SURVIVES debate with weak supporting evidence — but KB autopopulate fix has a 53-day-old documented breakage vs this being a speculative future bug. Better as run 72 candidate when next Agent OS service ships.
