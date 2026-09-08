# Nightly Commit Review — 2026-09-08

Run: automated, UTC 2026-09-08

## Commits Reviewed (last 24h)

| SHA | Message | Risk | Action |
|-----|---------|------|--------|
| 89b9e01 | chore(deps-dev): bump jsdom 29→30 in /frontend | LOW | No action (routine dep bump) |
| f8ba92b | chore(deps): bump uvicorn 0.49→0.52.4 in /backend | LOW | No action (routine dep bump) |
| 891dcbf | chore(deps-dev): bump @vitejs/plugin-react to 6.1.1 | LOW | No action (routine dep bump) |
| 776387d | chore(deps-dev): bump vitest group in demo-platform | LOW | No action (routine dep bump) |
| bee0ef1 | Merge PR #817 @testing-library/jest-dom bump | LOW | No action (merge) |
| ae15d43 | Merge PR #812 eslint bump | LOW | No action (merge) |
| c155ef1 | chore(deps-dev): bump @testing-library/jest-dom in /frontend | LOW | No action (routine dep bump) |
| 3896222 | chore(deps-dev): bump eslint 10.9.1→10.10.0 | LOW | No action (routine dep bump) |
| 0d86584 | ci(dependabot): group demo Vitest updates | LOW | No action (CI config) |
| ab458db | chore(deps-dev): bump @playwright/test 1.61.1→1.62.1 | LOW | No action (routine dep bump) |
| 3cc5be7 | ops: kb drift sweep 2026-09-07 — no drift detected | LOW | No action (routine ops) |
| 74792ea | chore: weekly skill discovery report 2026-09-07 | LOW | No action (routine ops) |
| 2c604eb | fix(os-workflows): remove postponed annotations (#806) | LOW | Verified correct fix (continuation of issue #805 cleanup) |
| 38c29ba | chore(deps-dev): bump vite 8.1.5→8.2.2 in /demo-platform | LOW | No action (routine dep bump) |
| 7d9f708 | ops: nightly-commit-review 2026-09-07 | LOW | No action (prior run) |

## Bugs Found and Fixed

### LOW: `from __future__ import annotations` in 2 service files

**Critical Invariant violation** — CLAUDE.md Rule 5 prohibits `from __future__ import annotations` in FastAPI backend files.

Files fixed in this run:
- `backend/services/website_connect.py` — imported by `backend/routers/website_connect.py` (FastAPI router). Uses `@dataclass`, not Pydantic models. All type annotations were defined before use (no forward references). Safe to remove.
- `backend/services/os_workflows/planner_bakeoff.py` — bakeoff script, not imported by any router. The one forward reference (`"BakeoffCaseResult"`) already used explicit string quotes. Safe to remove.

Both files passed `python3 -m py_compile` after fix.

## Medium Issues → GitHub Issues

### MEDIUM: `from __future__ import annotations` in 5 test files

5 test files still carry the import:
- `backend/tests/test_website_connect.py:16`
- `backend/tests/test_local_seo_handlers.py:8`
- `backend/tests/test_os_invoice_actions.py:8`
- `backend/tests/test_os_calendar_crm.py:3`
- `backend/tests/test_os_invoice_e2e.py:16`

Test files are not FastAPI route handlers so the 422-on-every-request risk doesn't apply. However, these violate the blanket backend rule and should be cleaned up as part of ongoing issue #805 cleanup.

→ GitHub issue created: see output below

## Summary

- 15 commits reviewed
- 13 dependency bumps: all LOW, no action
- 1 prior nightly review commit: no action
- 1 `from __future__` service file fix (issue #805 continuation): LOW, fixed in place
- 2 service files fixed: `website_connect.py`, `os_workflows/planner_bakeoff.py`
- 5 test files flagged as MEDIUM → GitHub issue for issue #805 backlog

No HIGH risk commits found. No auth/payment/schema changes. No action required from owner.
