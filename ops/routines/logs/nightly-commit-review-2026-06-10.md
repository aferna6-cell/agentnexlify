# Nightly Commit Review — 2026-06-10

Generated: 2026-06-10 UTC

---

## Commits reviewed (last 24h)

| SHA | Message | Risk | Verdict |
|-----|---------|------|---------|
| `1eb0a0f` | subconscious: run 2026-06-09-pm — Write os_action_dispatch.py test coverage | LOW | No issues. Docs/state only. |
| `ca3ce68` | ops: nightly-commit-review 2026-06-09 | LOW | No issues. Log + pre-commit hook. |
| `f4f2b96` | ops: morning-digest 2026-06-09 | LOW | No issues. Log only. |
| `c8a0460` | Agent OS knowledge graph: per-tenant long-term memory (migration 133) | MEDIUM | **BUG FIXED** — see below. |
| `369b3c8` | Agent OS Phase 4: engine-only cutover, real send, plan caps, conversational front door | MEDIUM | No bugs. Security analysis clean. |

---

## Bug Fixed (LOW risk — applied this run)

### `tenant_scope.py`: `os_graph_nodes` + `os_graph_edges` missing from `_TENANT_COLUMN_OVERRIDES`

**File:** `backend/services/tenant_scope.py`  
**Introduced by:** `c8a0460`  
**Severity:** Feature-breaking (graph memory writes/reads fail in production)

**Root cause:**  
`os_graph_memory.py` calls `tenant_table(db, "os_graph_nodes", client_id)` and `tenant_table(db, "os_graph_edges", client_id)`. `tenant_scope_column()` defaults unknown tables to `"tenant_id"`. Both tables use `"client_id"` per migration 133. All queries against these tables would fail at the database level (column `tenant_id` does not exist in `os_graph_nodes` / `os_graph_edges`).

Tests passed because `test_os_graph_memory.py` uses a mock DB that ignores column names.

**Fix:** Added two entries to `_TENANT_COLUMN_OVERRIDES`:
```python
"os_graph_nodes": "client_id",
"os_graph_edges": "client_id",
```
Consistent with 13 existing `os_*` entries using the same pattern.

**Commit:** this run.

---

## Test coverage added (AUTONOMOUS-EXECUTABLE — subconscious run 53)

### `backend/tests/test_os_action_dispatch.py` — 5 tests for `queue_action_for_run()`

`os_action_dispatch.py` (introduced in `369b3c8`) had no test coverage. Subconscious flagged as AUTONOMOUS-EXECUTABLE based on the `widget_enabled`-default-True incident analogy (2026-06-07, caught only in prod).

Covers all 5 execution paths:
1. No `action_type` → immediate `None`
2. Unknown `action_type` → `None`
3. Existing succeeded row → idempotent return (no re-insert)
4. New run with `BackgroundTasks` → `add_task` called
5. New run with `background=None` → `run_action` awaited inline

---

## Security analysis: Agent OS Phase 4 (`369b3c8`)

**Auto-send gate** (`agent_os_bridge.py:190-218`): requires all three to be true — engine says no approval needed, `tenants.os_auto_send_enabled=TRUE` (default FALSE), agent not in `NEVER_AUTO_SEND_AGENTS`. Failures default to `pending_approval` (safe side). **Clean.**

**Inbound webhook gate** (`os_inbound_bridge.py:437-447`): plan-tier usage cap enforced on inbound webhook path. Prevents cap bypass via email/SMS/Facebook/widget webhooks. **Clean.**

**Metadata redaction** (`os_inbound_bridge.py:560-578`): OAuth tokens, `client_secret`, `authorization` stripped from `source_metadata` before DB insert. **Clean.**

**Idempotency**: `_already_ingested()` check + UNIQUE partial index on `(client_id, source_ref)` prevents duplicate processing. **Clean.**

No auth/payments/tenant-isolation issues found.

---

## Schema discipline checks

- No `from __future__ import annotations` in FastAPI files. (Only in `backend/tests/test_local_seo_handlers.py` — test file, acceptable.)
- No `tenant_id` used on `leads` or `conversations` tables in new code.
- No `lead_stage` or `service_interest` column references.
- `os_graph_nodes` / `os_graph_edges` `client_id` pattern consistent with migration 133.

---

## No MEDIUM/HIGH issues requiring GitHub issues

All findings were either LOW-risk fixes (applied) or security-analyzed-clean MEDIUM-risk features.
