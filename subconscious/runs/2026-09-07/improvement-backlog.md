# Improvement Backlog — 2026-09-07

## Active
- Fix `from __future__ import annotations` in `backend/services/os_workflows/` (3 files: shadow_planner.py:15, planner_bakeoff.py:13, tool_catalog.py:21) — CLAUDE.md Rule #5 violation cluster, autonomous-executable, HIGH confidence

## Parking Lot (survived debate but not chosen)
- Fix Step 9G cloud trigger to use `mcp__github__actions_run_trigger` instead of `gh workflow run` — correct fix but insufficient alone while GH Actions secrets (ANTHROPIC_API_KEY, SUPABASE_ACCESS_TOKEN) remain unset; revisit after secret blockers resolved
- Split `os_tool_executions.py` god class (783L service + 411L router) — mandate requires 10d+ stability; last commit 2026-08-30 = 8d; eligible 2026-09-10+; split plan: executor_core + registry + results

## Rejected This Run
- Batch-file 20 check_ai_metering violations as GitHub issues — KILLED: Step 9L auto-files tonight, manual filing is duplicate work
- Remove Step 9J per-run Dependabot cap — KILLED: insufficient evidence of harm from 17-skip behavior; cap may protect CI rate limits

## Questions for Next Run
- Has the `from __future__ import annotations` fix been implemented? (autonomous-executable; should happen same day)
- Has os_tool_executions.py reached 10d+ stability threshold (2026-09-10)? Is it safe to split now?
- What is the first Step 9L violation report from the nightly (fires tonight 2026-09-07)? How many GH issues were auto-filed?
- Is SUPABASE_ACCESS_TOKEN now set in GH Actions? (GH #800 follow-up from run 118 mandate)
