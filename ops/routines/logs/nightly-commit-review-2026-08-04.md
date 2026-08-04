# Nightly Commit Review — 2026-08-04

**Run time:** 2026-08-04 (UTC) | **Commits reviewed:** 4 | **Issues filed:** 0

---

## Commits

### 1. `4853c31` feat: typed knowledge notes — tenants add KB entries by typing (#632) [skip ci]
**Risk:** MEDIUM  
**Author:** aferna6-cell  
**Files:** `backend/routers/tenant_kb.py`, `backend/tests/test_tenant_kb.py`, `frontend/src/pages/KnowledgeSourcesPage.jsx`, `frontend/src/utils/api/tenant-kb.js`, `frontend/src/pages/IntegrationsPage.jsx`

**Summary:** New `POST /api/v1/kb/{tenant_id}/notes` endpoint. Tenants can type knowledge directly into the dashboard (pricing, policies, service details) without uploading a file. Same ingest spine as file uploads — notes land in `tenant_kb_documents` with `source='note'`, keyed by title slug so re-saving updates in place. Plan doc limit enforced on new notes only; edits bypass the limit. 8 new tests added (156 total passing per commit message).

**Invariant checks:**
- `client_id` ✅ — Service call uses `upsert_document(tenant_id, ...)` which maps to the `client_id` positional parameter
- No `from __future__ import annotations` ✅ — File header comment prohibits it; not present in diff
- Cross-tenant isolation ✅ — `_require_tenant(claims, tenant_id)` called immediately in route handler
- Plan gating ✅ — Limit checked against `doc_limit_for_plan(_resolve_plan(...))` before inserting new notes
- Pydantic validation ✅ — `Field(..., min_length=1, max_length=...)` on both `title` and `content`

**Notes:**
- `HTTPException` raised inside `_ingest()` closure via `run_in_threadpool` — valid FastAPI pattern; `anyio.to_thread.run_sync` propagates exceptions back to the event loop where Starlette middleware catches them. No issue.
- `IntegrationsPage.jsx` em-dash → hyphen fix bundled in. Minor, obviously correct.

**Decision:** No issues. MEDIUM feature shipping cleanly.

---

### 2. `54f3ad7` ops: kb-drift sweep 2026-08-03 — no drift detected
**Risk:** LOW  
**Summary:** Ops log only. No drift found in `plans/` directory.

---

### 3. `d6da4b4` ops: morning-digest 2026-08-03
**Risk:** LOW  
**Summary:** Ops log only. Morning digest routine output.

---

### 4. `227526a` ops: nightly-commit-review 2026-08-03 [auto-nightly]
**Risk:** LOW  
**Summary:** Previous nightly review log. No issues were found on 2026-08-03.

---

## Outcome

| Risk level | Count | Action |
|------------|-------|--------|
| HIGH | 0 | — |
| MEDIUM | 1 | No bugs found — no issue filed |
| LOW | 3 | Ops logs only — no action |

**LOW-risk fixes applied:** none  
**GitHub issues filed:** none  
**Overall status:** Clean. No action required.
