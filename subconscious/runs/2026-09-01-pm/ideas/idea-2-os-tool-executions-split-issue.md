# Idea 2 — File GH Issue for os_tool_executions.py God-Class Split

**Category:** code_health / workflow
**Effort:** XS
**Autonomous-executable:** YES (file issue only, not implement split)

## Evidence
- `backend/services/os_tool_executions.py`: 772 lines (god-class threshold 600L)
- Committed 2026-09-01 (today): stability check FAILS (need 4d+ with 0 commits)
- run_115_mandate condition: "if stable (0 commits 4d+): run 115 god class split candidate"
- No GH issue filed for split yet — subconscious will re-discover next run otherwise

## Action
File GH issue now with:
- Title: "Refactor: split os_tool_executions.py god class (772L → 3 modules)"
- Labels: `ai-ready, refactor, tech-debt`
- Body: implementation sketch (split into _crud, _approval, _billing modules)
- Note: "Hold until 4d+ with 0 commits (last commit: 2026-09-01)"

## Impact
Eliminates repeat subconscious rediscovery.
Queues work for issue-to-pr-loop when stability condition met.
Costs zero additional tokens to file — minimal effort, clear dedup win.

## Verdict
**WEAKENED** — valid but mandate stability condition unmet today (file committed 2026-09-01).
Deferred to run 117. Will be picked if file stable by then.
