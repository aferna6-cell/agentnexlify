# Nightly Commit Review — 2026-05-11

**Window:** last 24 hours  
**Commits reviewed:** 1  
**Issues found:** 0  
**Fixes applied:** 0  
**GH issues opened:** 0

---

## Commits Triaged

### 21ab211 — `ops: nightly-commit-review 2026-05-10` — LOW
- Adds `ops/routines/logs/nightly-commit-review-2026-05-10.md`
- Automated log only. No production code. No action needed.

---

## Automated Checks

| Check | Result |
|-------|--------|
| Widget 3-copy sync | PASS — `widget/` and `frontend/public/widget/` byte-identical |
| Project invariants (`check_project_invariants.py`) | PASS — all 6 checks passed |
| FastAPI future annotations (routers/services) | PASS — no violations (`branding_helpers.py` warning comment is protective, not an import) |
| Schema field naming (client_id, status, areas_of_interest) | PASS |
| `leads` + `conversations` queries use `client_id` | PASS — verified `csat.py`, `sms.py` both correct |
| Retired plan names | PASS |
| Em-dash in website source | PASS |
| SDK wrapper enforcement | PASS |

---

## Observations (pre-existing, not introduced by 24h commits)

### 1. `from __future__ import annotations` in test file
- **File:** `backend/tests/test_local_seo_handlers.py:8`
- **Risk:** None. Test files do not define Pydantic models resolved by FastAPI. Pre-existing, unchanged.

### 2. `tenant_id` local variable in `backend/routers/sms.py`
- **Assessment:** CORRECT. JWT claim extraction uses `tenant_id` name; all DB queries on `leads`/`conversations` correctly use `.eq("client_id", tenant_id)`. Verified again this session.

### 3. `service_interest` in field mapping dicts
- **Files:** `backend/routers/leads.py:538`, `backend/routers/widget_lead_helpers.py:413-417`
- **Assessment:** CORRECT. These are incoming-field alias handlers that translate `service_interest` → `areas_of_interest` in DB writes. No column named `service_interest` is ever queried.

### 4. `tenant_id` in non-leads/conversations tables
- **Files:** `scoring_config.py` (`scoring_configs` table), `csat.py` (`csat_responses` table), `webhook_deliveries.py`, `managed_agent_runs.py`
- **Assessment:** CORRECT. CLAUDE.md critical rule applies to `leads` + `conversations` tables only. These tables legitimately use `tenant_id` as their FK column name.

---

## Informational: Subconscious Moratorium Status (carried forward)

Not a nightly-review finding — flagged for human visibility only.

4 pending approvals remain in subconscious governance (unchanged since 2026-05-09):
- **Run 7/15** — Widget 3-Copy Sync Guard (~30 min)
- **Run 8** — Wire `check_project_invariants.py` into pre-commit (~5 min)
- **Run 14** — Wire lead qualifier golden eval to CI (~20 min)
- **Run 4** — AI-to-Human Handoff v1 (23+ days pending, M-effort)

These require human go/no-go — not auto-implementable per nightly review scope.

---

## Summary

No bugs or issues found in the 24-hour commit window. One LOW-risk automated commit (prior nightly log). All 6 invariant checks pass. Pre-existing observations re-verified — all confirmed non-issues.
