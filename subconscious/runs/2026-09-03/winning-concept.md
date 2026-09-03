# Winning Concept — Run 115 (2026-09-03)

## Recommendation
Remove the dead inner guard in `backend/services/os_workflows/engine.py:derive_workflow_status()` (lines 108–110): the outer `all(s in {"succeeded", "cancelled"})` check already excludes `"failed"` and `"unknown"`, making the inner `if all(s != "failed" and s != "unknown" ...)` permanently True and its return unreachable without the inner guard.

## Why This, Why Now
nightly-2026-09-03 explicitly flagged this dead guard as a code note in the M9.2 triage and deferred cleanup with "new major module, autonomous cleanup deferred." The subconscious backing this recommendation makes it actionable in the next nightly cycle. The inner guard creates a maintenance trap: a future developer could remove the outer guard while trusting the inner one provides protection — but the inner guard provides no independent coverage. M9.2 is brand-new (landed 2026-09-02), and establishing clean code standards now prevents confusion as the module grows through M9.3+.

## Implementation Sketch
1. Edit `backend/services/os_workflows/engine.py` — function `derive_workflow_status()`, starting at line 105:

**Current (lines 105–110):**
```python
if all(s in {"succeeded", "cancelled"} for s in states) and any(
    s == "succeeded" for s in states
):
    # All finished; succeed if at least one succeeded and none failed/unknown.
    if all(s != "failed" and s != "unknown" for s in states):
        return "succeeded"
```

**Replace with:**
```python
if all(s in {"succeeded", "cancelled"} for s in states) and any(
    s == "succeeded" for s in states
):
    return "succeeded"
```

2. Commit: `fix(m9): remove dead guard in derive_workflow_status [skip ci]`
3. No migration, no new deps, no test changes needed — the existing test_os_workflows_engine.py already exercises this path and will continue to pass.

## What This Replaces
Previous active direction was Step 9K (stale subconscious PR audit — implemented run 114). Step 9K is confirmed working in nightly-2026-09-03.

## Confidence
**HIGH** — nightly-2026-09-03 called it out by name; direct code read at lines 105-110 confirms the redundancy; 3-line deletion with zero behavioral change; nightly can execute as LOW-risk bug patch on an existing file.

## Run 116 Mandate
1. Verify dead guard removed: `grep -n "s != .failed. and s != .unknown." backend/services/os_workflows/engine.py` should return 0 results.
2. test_os_workflows_engine.py still passes (290+ tests).
3. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway? Brain connector health (42d+ stale).
4. os_tool_executions.py stability: `git log --since="4 days ago" -- backend/services/os_tool_executions.py` returns empty? If yes: propose god class split as run 116 winner.
5. GH #728 ai-ready: file `test_os_workflows_store.py` as ai-ready GH issue (loop will handle when GH #399 resolves).
6. Step 9J: did Dependabot PRs #721/#722 become clean + merge after rebase trigger?
