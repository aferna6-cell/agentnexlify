# Idea 5: Audit `__future__` Annotations Pre-commit Coverage Gap

**Evidence:** nightly-2026-08-31 auto-fixed m8_action_flags.py removing `from __future__ import annotations`. Pre-commit hook blocks this pattern (established invariant — CLAUDE.md critical rule #5). The M8 sprint is generating new service files rapidly (m8_action_flags.py is one of many); the pre-commit hook should have caught this before commit. Either: (a) the file was committed in a bypass session, or (b) the pre-commit hook has a coverage gap for new service paths.

**Action:** Check pre-commit hook scope for `from __future__ import annotations` — verify it covers all of backend/services/ including new M8 subdirectories (m8_action_flags.py likely in a new path not covered). If gap found: extend hook glob pattern. Estimated: 5 lines.

**Impact:** Prevents nightly cleanup cycles for a well-known invariant. Each `__future__ annotations` that slips in causes Pydantic failures — the nightly catch means production risk window exists between commit and nightly run.

**Category:** code_health
