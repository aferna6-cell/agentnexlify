# Idea 04 — os_tool_executions.py God Class Split

## Category
code_health

## Summary
Split `backend/services/os_tool_executions.py` (758 lines, >600 god-class threshold) into focused modules per user-rules.md Rule 9.

## Evidence
- os_tool_executions.py: 758 lines, last commit 2026-08-30 22:04 (today)
- Rule 9: files >600 lines → split before adding more
- Run 113 mandate: "os_tool_executions.py: stable now (3+ days no commits)? If yes, run 114 candidate for god class split"
- File committed today — NOT stable for 3d+ yet (condition: fails)
- Contains calendar ops, CRM ops, tool routing — multiple distinct concerns

## Implementation (when stable)
1. `backend/services/os_calendar_tools.py` — calendar action handlers
2. `backend/services/os_crm_tools.py` — CRM action handlers  
3. `backend/services/os_tool_router.py` — dispatch + routing
4. Update all imports in `main.py` and routers

## Blocker
File last modified today (2026-08-30 22:04) — not stable for 3+ days. Defer until run 117+ when no commits for 72h.

## Risk
MEDIUM when stable, HIGH if split mid-sprint — defer

## Confidence
HIGH on need, LOW on timing — deferred
