# Improvement Backlog — Run 115 (2026-09-03)

## Active
- Remove dead inner guard in `derive_workflow_status()` (`backend/services/os_workflows/engine.py` lines 108–110) — XS effort, nightly-executable, 3-line deletion.

## Parking Lot (survived debate, not chosen)
- **Add `test_os_workflows_store.py`** — File as ai-ready GH issue for issue-to-PR loop when GH #399 resolves. M-effort, HIGH value for new DB-touching module.
- **Step 9L: auto-enrich bug-patterns.md Details** — Needs cleaner diff-read mechanism. Re-evaluate when nightly Step 9A is enhanced to parse commit diffs.

## Deferred (mandate condition not met)
- **os_tool_executions.py god class split** — 775 lines, 29% over threshold. Deferred: last commit 2026-09-01 (not stable). Re-propose as run 116 winner when `git log --since="4 days ago" -- backend/services/os_tool_executions.py` returns empty.

## Rejected This Run
- **Step 9L (dead code enrichment)** — WEAKENED: nightly triage summaries not high enough quality for reliable root cause notes without reading diffs; risk of misleading entries in bug-patterns.md.

## Questions for Next Run
1. Is the dead guard fix in production? If nightly didn't execute it (LOW-risk channel), should subconscious implement directly?
2. Has os_tool_executions.py reached 4-day stability? If yes, god class split becomes the winner.
3. GH #684 SUPABASE_ACCESS_TOKEN — has 42-day brain connector stall been resolved? If not, is there a harder escalation beyond Step 9C comments?
