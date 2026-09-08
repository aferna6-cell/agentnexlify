# Winning Concept — Run 118 (2026-09-08-pm)

## Title
os_tool_executions.py God Class Split

## Category
code_health

## Confidence
HIGH

## Evidence
- File: `backend/services/os_tool_executions.py`, 783 lines
- Last commit: `fdcbb97 fix(m9): M9.4 bakeoff miss classification (#773)` — NOT in 7-day window = 10d+ stable
- Rule 9 violation: >600 lines, adding any concern is prohibited without split
- Governance mandate set in run 117: "run 118 winner IF Step 9L confirmed AND file still stable"
- Step 9L confirmed via `grep -c 'Step 9L' .claude/skills/nightly-commit-review/SKILL.md` → 2
- M8 development paused: safe split window exists now

## Action
File a GitHub issue recommending the split into 3 focused modules with module boundary sketch. Do NOT implement.

**Issue title:** `refactor(m8): split os_tool_executions.py god class (783L) into 3 focused modules`

**Issue body outline:**
- Context: file at 783L, Rule 9 requires split before next addition; last commit 10d+ ago = safe window
- Proposed module boundaries:
  - `os_execution_engine.py` — core execution loop, job state machine, retry/timeout logic
  - `os_tool_dispatcher.py` — tool routing, catalog adapter, tool-to-handler mapping
  - `os_result_formatter.py` — output normalization, result schema, logging/tracing output
- Acceptance criteria: all three modules pass existing tests, no new public API surface, no behavior change
- Labels: `code_health`, `m8`, `refactor`, `medium-effort`
- Blocking relationship: blocks next M8 sprint that adds new tool handlers

## Why This Wins
1. **Governance mandate**: explicitly queued two runs ago with exact preconditions (Step 9L confirmed + 10d+ stable). Preconditions cleared this run. Delivering on a queued mandate is the highest-priority subconscious action.
2. **Rule 9 enforcement**: 783L file violates the 600L god class threshold. Any future M8 addition without a split makes the problem worse.
3. **Safe window**: M8 paused means no concurrent development. Recommending the split now gives the human sprint lead a clean opportunity to act before M8 resumes.
4. **Low risk**: a GH issue recommendation is zero-risk output — human decides the split details and timing.

## Runner-Up (not implemented — file as separate issue or PR)
**Extend `from __future__` CI check to all `backend/*.py`**
Two-line change in `pr-check.yml` (line ~121) and `health-check.yml` (line ~58): change `backend/routers/` → `backend/`. Eliminates the recurring nightly cleanup of annotations pattern. Strong evidence: issues #805 and #823 filed on consecutive days for pattern spreading to services/ and tests/. This could be a second deliverable from this run — subconscious can file a second GH issue for it.
