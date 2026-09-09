# Winning Concept — Run 118 (2026-09-09)

## Recommendation

Split `backend/services/os_tool_executions.py` (783L, 10d+ stable) into three focused modules before the next OS workflow feature lands.

## Why This, Why Now

`os_tool_executions.py` at 783L is the clearest god class in the backend. Run 116 governance mandate named this as the run 118 candidate contingent on Step 9L confirmation; Step 9L was confirmed implemented via PR #804 (`ci(nightly): wire Step 9L AI metering sweep`). CLAUDE.md Rule 9 is explicit: at 600+ lines, split before adding. The OS workflow feature area is actively growing — PRs #771 (invoicing E2E) and #803 (tenant graph AI billing) both touched os-workflows in the past 7 days. The file has been stable for 10d+ with no in-flight changes, making this the optimal split window. Post-split, each new OS feature targets a 260L file instead of a 783L monolith, cutting review surface and blast radius for future bugs.

## Implementation Sketch

1. **Audit current structure** — read `os_tool_executions.py` end-to-end, identify logical boundaries:
   - Routing/dispatch (which tool handles which intent)
   - Per-tool handler functions (the actual execution logic)
   - Shared context/state (client_id propagation, error wrapping)

2. **Create three new files:**
   - `backend/services/os_tool_dispatch.py` — intent routing, tool selection, orchestration (~260L)
   - `backend/services/os_tool_handlers.py` — per-tool execution functions (~260L)
   - `backend/services/os_tool_context.py` — shared context helpers, error wrapping, logging (~260L)

3. **Update imports** — find all call sites of `os_tool_executions`:
   ```bash
   grep -rn "from.*os_tool_executions\|import.*os_tool_executions" backend/
   ```
   Update each to import from the correct new module.

4. **Keep a thin shim** `backend/services/os_tool_executions.py` that re-exports the old public API:
   ```python
   from backend.services.os_tool_dispatch import *  # noqa
   from backend.services.os_tool_handlers import *  # noqa
   ```
   This allows gradual migration without breaking all call sites at once.

5. **Run existing tests:**
   ```bash
   python -m pytest backend/tests/ -x -q --tb=short
   ```
   All tests should pass with zero behavior change.

6. **Verify no circular imports:**
   ```bash
   python -c "from backend.services.os_tool_dispatch import *"
   python -c "from backend.services.os_tool_handlers import *"
   python -c "from backend.services.os_tool_context import *"
   ```

7. **Remove shim** — once all call sites updated, delete the re-export shim and confirm CI green.

8. **Update `backend/CONTEXT.md`** — add entries for all three new modules.

## What This Replaces

Step 9L (AI metering coverage sweep) was the previous active direction — **implemented** via PR #804.
This run opens a fresh active direction slot for the god class split.

## Confidence

**HIGH** — governance mandate explicitly named this. File is stable (10d+, 1 commit in history).
Pure refactor with identical behavior: all existing tests validate correctness. CLAUDE.md Rule 9
directly applies. OS workflow area is actively growing — split before next feature lands.
