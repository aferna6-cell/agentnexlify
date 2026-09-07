# Winning Concept — 2026-09-07

## Recommendation
Remove `from __future__ import annotations` from all three `backend/services/os_workflows/` files (`shadow_planner.py:15`, `planner_bakeoff.py:13`, `tool_catalog.py:21`).

## Why This, Why Now
Today's nightly commit review (run on 2026-09-07) identified `shadow_planner.py:15` as carrying the banned import (added in commit `6063bbb`, PR #780) and filed a GH issue with label `nightly-review`. The same pattern already exists in `planner_bakeoff.py:13` and `tool_catalog.py:21` — three files spreading the annotation across the os_workflows directory. CLAUDE.md Rule #5 explicitly bans this import in FastAPI files because PEP 563 deferred annotations cause Pydantic to resolve model bodies as strings, silently breaking validation at runtime. M9 is actively adding files to os_workflows (2 new files per week), meaning this cluster will grow. The fix is 3 one-line deletions, autonomous-executable, and eliminates the future 422 risk entirely before any of these files gains a Pydantic model or enters the FastAPI import chain.

## Implementation Sketch
1. Read `backend/services/os_workflows/shadow_planner.py` — confirm line 15 is `from __future__ import annotations`, scan for `X | Y` union type syntax that would break without the import.
2. Delete the import line from `shadow_planner.py`.
3. Read `backend/services/os_workflows/planner_bakeoff.py` — confirm line 13, same scan.
4. Delete the import line from `planner_bakeoff.py`.
5. Read `backend/services/os_workflows/tool_catalog.py` — confirm line 21, same scan.
6. Delete the import line from `tool_catalog.py`.
7. Run `python -c "import backend.services.os_workflows.shadow_planner; import backend.services.os_workflows.planner_bakeoff; import backend.services.os_workflows.tool_catalog"` to confirm imports succeed.
8. Run `python -m pytest backend/tests/ -x -q --tb=short 2>&1 | tail -20` to confirm no regressions.
9. Commit: `fix(os_workflows): remove banned __future__ annotations import from 3 files`.

## What This Replaces
Previous active direction: Step 9L AI metering coverage (carry-forward 3 runs, now IMPLEMENTED as of commit `88dac49` on 2026-09-06). Step 9L is complete — nightly sweep wired, test suite at 325 lines, 20+ violations identified for automated filing. No further subconscious tracking needed on that direction.

## Confidence
HIGH — CLAUDE.md hard rule, nightly detected and filed issue today, 3-line fix, zero-risk change, autonomous-executable.
