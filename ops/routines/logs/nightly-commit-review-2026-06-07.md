# Nightly Commit Review — 2026-06-07

Generated: 2026-06-07 (UTC)  
Window: last 24 hours  
Commits reviewed: 4

---

## Commit Triage

### 1. `abccdc3` — Harden agent-service auth before v2 engine activation (#205)
**Risk: HIGH**  
**Files:** `agent-service/src/auth.ts`, `agent-service/src/auth.test.ts`, `agent-service/src/server.ts`, `agent-service/DEPLOY.md`, `backend/services/agent_sdk_client.py`, `backend/tests/test_agent_sdk_client.py`

Auth layer added between FastAPI backend and Node agent-service. Backend attaches `X-Agent-Token` header when `AGENT_SERVICE_TOKEN` env var is set; agent-service rejects compute routes with 401 when header is missing or wrong. `/health` stays open for Railway healthcheck. Token check is correctly placed before all compute routes in `server.ts`.

**Issue found → GitHub #206 (MEDIUM severity, HIGH label):**  
`isTokenAuthorized` in `auth.ts` uses JavaScript `===` for secret comparison, which is not constant-time. Timing attacks are possible if the service ever gets a public network route. Fix: replace `===` with `crypto.timingSafeEqual`. Risk is currently reduced by Railway private networking.

**Schema discipline:** N/A (no Python backend schema changes in this commit).  
**`__future__` annotations:** None in new FastAPI files.  
**Action:** Issue #206 filed. No auto-fix (auth code — requires human approval).

---

### 2. `cefed42` — docs: auto-log bug fix from 2287f6b
**Risk: LOW**  
**Files:** `docs/dev-knowledge/bug-patterns.md`

Automated doc entry logging the widget hijack bug found in commit `2287f6b`. Pure documentation, no code changed.

**Issues found:** None.  
**Action:** None required.

---

### 3. `2287f6b` — Fix: Agent OS no longer hijacks the public chat widget (#204)
**Risk: MEDIUM**  
**Files:** `backend/services/os_inbound_bridge.py`, `backend/tests/test_os_inbound_bridge.py`

Flipped `_DEFAULT_CONFIG["widget_enabled"]` from `True` to `False`. Agent OS is now opt-in for the public chat widget — dashboard-only by default. Regression test added that pins the default to `False`.

**Issues found:** None. Fix is correct; widget byte-identical constraint not affected (this is backend routing logic, not widget JS). Regression test validates the invariant.  
**Action:** None required.

---

### 4. `7a621a1` — Adopt demo agent framework as Agent OS orchestration core (#203)
**Risk: HIGH**  
**Files:** 96 files, 7,640 insertions — new `agent-service/src/agent-os/` engine, `backend/services/agent_os_bridge.py`, `backend/routers/os_orchestrate.py`, `migrations/131_os_engine_telemetry.sql`, frontend pages/utils, `plans/agent-os-demo-merge_plan.md`

Major architectural change: FastAPI/Supabase demoted to data/identity plane; vendored agent-os engine in agent-service becomes orchestration core. Engine activates only when `AGENT_SERVICE_URL` is set (deploy-order safe). Includes migration 131 adding `os_routing_decision` and `os_model_call_log` tables.

**Schema discipline checks (CLAUDE.md Critical Rules):**
- `client_id` not `tenant_id`: ✅ All Supabase queries in `agent_os_bridge.py` use `client_id` via `tenant_table()`. `os_orchestrate.py` pulls `client_id = claims["tenant_id"]` from JWT — correct pattern.
- Migration 131: ✅ Both new tables (`os_routing_decision`, `os_model_call_log`) are `client_id`-scoped.
- `__future__ import annotations`: ✅ Not present in any new FastAPI files (`os_orchestrate.py`, `agent_os_bridge.py`, `agent_sdk_client.py`).
- RLS: ✅ Migration enables RLS on both new tables with deny-public policy.

**Tests per commit message:** backend 8/8, frontend 38/38, agent-service 14/14 — all passing at merge.

**Issues found:** None beyond the auth concern filed under commit `abccdc3`. Code is clean against all CLAUDE.md invariants.  
**Action:** None required. Note: migration 131 must be applied to production Supabase if not already done.

---

## Summary

| Commit | Risk | Action |
|--------|------|--------|
| `abccdc3` auth hardening | HIGH | Issue #206 filed (timing-safe token comparison) |
| `cefed42` docs | LOW | None |
| `2287f6b` widget fix | MEDIUM | None (clean fix) |
| `7a621a1` Agent OS engine | HIGH | None (code clean; verify migration 131 applied in prod) |

**Issues filed:** 1  
**Auto-fixes applied:** 0  
**CLAUDE.md invariant violations found:** 0
