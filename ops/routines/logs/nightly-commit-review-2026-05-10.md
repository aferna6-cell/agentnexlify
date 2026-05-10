# Nightly Commit Review — 2026-05-10

**Window:** last 24 hours  
**Commits reviewed:** 1  
**Issues found:** 0  
**Fixes applied:** 0  
**GH issues opened:** 0

---

## Commits Triaged

### e821a68 — `ops: nightly-commit-review 2026-05-09` — LOW
- Adds `ops/routines/logs/nightly-commit-review-2026-05-09.md`
- Automated log only. No production code. No action needed.

---

## Automated Checks

| Check | Result |
|-------|--------|
| Widget 3-copy sync | PASS — `widget/` and `frontend/public/widget/` byte-identical |
| Project invariants (`check_project_invariants.py`) | PASS — all 6 checks passed |
| FastAPI future annotations (routers/services) | PASS — no violations in production code |
| Schema field naming (client_id, status, areas_of_interest) | PASS |
| Retired plan names | PASS |
| Em-dash in website source | PASS |
| SDK wrapper enforcement | PASS |

---

## Pre-existing Observations (not from 24h window — not actioned)

### 1. `from __future__ import annotations` in test file
- **File:** `backend/tests/test_local_seo_handlers.py:8`
- **Risk:** Not a production issue. Test files do not define Pydantic models resolved by FastAPI. The critical rule (no `__future__` in FastAPI files) targets routers and services. No 422 risk. Pre-existing — not introduced by any commit in the 24h window.

### 2. `tenant_id` local variable in `backend/routers/sms.py`
- **Lines:** 38, 43, 46, 54, 64, 66, 96, 102, 113, 120
- **Assessment:** CORRECT usage. `tenant_id = claims["tenant_id"]` extracts the identifier from the JWT payload (where the field is legitimately named `tenant_id`). All database queries against `leads` and `conversations` correctly use `.eq("client_id", tenant_id)`. The `tenants` table is queried with `.eq("id", tenant_id)` which is also correct. Schema discipline is maintained — DB column is `client_id`, local variable happens to mirror the JWT claim name. No action needed.

---

## Informational: Subconscious Moratorium Status (carried forward)

Not a nightly-review finding — flagged for human visibility only.

From prior review (2026-05-09): 4 pending approvals remain in subconscious governance.
- **Run 7/15** — Widget 3-Copy Sync Guard (~30 min)
- **Run 8** — Wire `check_project_invariants.py` into pre-commit (~5 min)
- **Run 14** — Wire lead qualifier golden eval to CI (~20 min)
- **Run 4** — AI-to-Human Handoff v1 (23+ days pending, M-effort)

These require human go/no-go — not auto-implementable per nightly review scope.

---

## Summary

No bugs or issues found in the 24-hour commit window. One LOW-risk automated commit (prior nightly log). All invariant checks pass. Two pre-existing observations noted but not actioned — both confirmed non-issues on closer inspection.
