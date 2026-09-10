# Winning Concept — Run 118 (2026-09-10)

## Recommendation
Split `backend/services/os_tool_executions.py` (783L) into three focused modules: `os_tool_executions_store.py`, `os_tool_executor.py`, and `os_tool_approval.py`.

## Why This, Why Now

`os_tool_executions.py` has crossed the 600L Rule 9 threshold by 183 lines and handles three distinct concerns in one file: data persistence (store), execution orchestration (executor), and human approval flow (approval_handler). The file has been stable for 10+ days since commit `f72a274` (schema docs only), making now the lowest-risk window for a clean split. Governance mandates from runs 116 and 117 both explicitly named this as "run 118 winner if Step 9L confirmed" — and Step 9L IS confirmed (grep returns 2 hits in SKILL.md, lines 457+471). The mandate binding plus evidence of stability plus Rule 9 threshold all converge on the same action.

## Implementation Sketch

1. **Audit current structure** — read `os_tool_executions.py` top-to-bottom, identify the three concern boundaries: (a) DB reads/writes for os_tool_executions table, (b) execution dispatch and retry logic, (c) approval gate, approval resolution, and human-action callbacks.

2. **Create `os_tool_executions_store.py`** — move all DB interaction functions (get_execution, create_execution, update_execution_status, list_pending_executions, etc.). Import only Supabase client + models. No business logic.

3. **Create `os_tool_executor.py`** — move execution dispatch, retry logic, tool selection, and result processing. Imports from `os_tool_executions_store` for persistence. This is the core orchestration layer.

4. **Create `os_tool_approval.py`** — move approval request creation, human-decision handling, approval timeout logic, and approval callbacks. Imports from `os_tool_executions_store` for persistence.

5. **Update `os_tool_executions.py`** — reduce to a re-export shim for backward compatibility: `from .os_tool_executor import *` + `from .os_tool_approval import *` + `from .os_tool_executions_store import *`. This protects all existing import sites without requiring them to change.

6. **Verify imports** — `grep -rn "os_tool_executions" backend/ --include="*.py"` to find all call sites. Confirm they all work through the shim. Run existing OS workflows tests: `python3 -m pytest backend/tests/test_os_*.py -x -q`.

7. **No API changes** — this is a pure internal refactor. No migration, no Pydantic model changes, no route changes.

## What This Replaces

No prior active direction replaced — Step 9L (now implemented) was the previous active direction. This is a net-new direction triggered by governance mandate.

## Confidence

**HIGH** — Three independent signals converge: (1) governance mandate binding from two consecutive runs, (2) Rule 9 threshold exceeded (183L over limit), (3) 10d file stability reducing split risk. The only uncertainty is in the split boundary discovery (Step 1 of implementation sketch) — the three concerns may share more than expected. The backward-compat shim (Step 5) removes the import-site risk entirely.
