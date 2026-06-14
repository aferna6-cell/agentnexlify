### Idea 1: Fix `channels_instagram.py` `from __future__ import annotations` — Production 422 Bug

**Evidence:** `check_project_invariants.py` exits 1 with "FAIL FastAPI router files avoid future annotations — backend/routers/channels_instagram.py". Direct grep confirms `from __future__ import annotations` on line 1. Introduced by 7c8825c (Home redo + Instagram connector, PR #232, merged 2026-06-11). CLAUDE.md Critical Invariant #5: "PEP 563 deferred annotations make Pydantic resolve bodies as strings → every request 422s." channels_instagram.py is 444L with full Pydantic request/response models. Every POST/GET to Instagram endpoints currently returns 422 validation errors.

**Action:** Remove line 1 (`from __future__ import annotations`) from `backend/routers/channels_instagram.py`. Verify `python3 scripts/check_project_invariants.py` reports 1 fewer failure.

**Impact:** All Instagram integration API endpoints become functional. AUTONOMOUS-EXECUTABLE — 1-line delete, same safety class as prior nightly fixes. Partially restores check_project_invariants (future-annotations check passes; em-dash check still fails until Idea 3 is applied).

**Category:** code_health
