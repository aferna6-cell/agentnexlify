# Nightly Commit Review — 2026-09-07

**Run window:** last 24 hours from 2026-09-07 UTC  
**Commits reviewed:** 11  
**Issues created:** 1  
**Fixes applied:** 0  

---

## Commit Triage

| SHA | Message | Risk | Action |
|-----|---------|------|--------|
| `22c4eed` | chore(deps-dev): bump @vitejs/plugin-react to 6.1.1 in /demo-platform | LOW | None |
| `6293503` | chore(deps-dev): bump eslint from 10.7.0 to 10.9.1 | LOW | None |
| `88dac49` | ci(nightly): wire Step 9L AI metering sweep (#804) | LOW | None |
| `47f14d3` | fix(billing): meter tenant graph AI calls (#803) | MEDIUM | See note |
| `7d61bc8` | subconscious: run 2026-09-06-pm — Step 9L AI metering SKILL.md block | LOW | None |
| `1c5b749` | feat(billing): add Step 9L AI metering detector (#802) | LOW | None |
| `86a0767` | chore(deps-dev): bump @typescript-eslint/parser to 8.69.0 | LOW | None |
| `b4389d6` | subconscious: run 2026-09-06 — Step 9L AI metering coverage | LOW | None |
| `6063bbb` | feat(m9): offline M9.5 shadow-path skeleton (zero I/O) (#780) | MEDIUM | Issue created |
| `b705708` | test(billing): dry-run staging smoke harness (#779) | LOW | None |
| `9f7f777` | ops: nightly-commit-review 2026-09-06 | LOW | None |

---

## MEDIUM — `6063bbb` shadow_planner.py `from __future__ import annotations`

**File:** `backend/services/os_workflows/shadow_planner.py` line 15  
**Rule:** `backend/CONTEXT.md` — "NEVER use `from __future__ import annotations`"  
**Finding:**  
`shadow_planner.py` (added in #780) imports `from __future__ import annotations`. The file uses Python `@dataclass` (not Pydantic models), is not imported by any FastAPI routes (only by tests), and follows an existing pattern in the same directory (`planner_bakeoff.py:13`, `tool_catalog.py:21`).

**Assessment:** Active risk is LOW — no Pydantic models defined, not in FastAPI import chain. However, `backend/CONTEXT.md` says NEVER, and the pattern is spreading in `os_workflows/`. If any of these files gains a Pydantic model or FastAPI route import in the future, the annotation will silently break validation.

**Action:** GitHub issue `nightly-review` label tracking the os_workflows `from __future__` inconsistency.

---

## MEDIUM — `47f14d3` graph AI metering (billing)

**Files:** `backend/graph/adapters/llm.py`, `tests/test_graph_ai_metering.py`  
**Finding:** Adds tenant-scoped AI token reservation/recording to every graph `agent_node` call when `ctx.tenant_id` is set. Code inspection shows:
- Reservation released on API call exception ✓
- Reservation released on recording failure ✓  
- `client_id` rule not applicable here — `tenants` table uses `id` column ✓
- `from __future__ import annotations` NOT present ✓
- 215 test lines added covering lifecycle ✓

**Assessment:** No bugs found. Well-tested. No action required.

---

## LOW fixes applied

None — no LOW-risk bugs found in reviewed commits.

---

## Summary

Healthy commit batch. Main concern is the spreading `from __future__ import annotations` pattern in `backend/services/os_workflows/`. Not a current breakage but a future maintenance risk flagged as GH issue. Billing metering changes (#803) are structurally sound.
