# Nightly Commit Review — 2026-06-08

**Window:** last 24 hours (2026-06-07 → 2026-06-08)
**Commits reviewed:** 3
**Issues filed:** 0
**Fixes applied:** 0

---

## Commits

### 1. `fff7193` — ops: nightly-commit-review 2026-06-07
**Risk:** LOG / no-op
Previous nightly review log commit. No code changes. No action needed.

---

### 2. `617b667` — Render v2 Agent OS response shape in the dashboard (#207)
**Risk:** LOW
**Files:** `.railwayignore`, `frontend/src/components/os/AgentRunFlowchart.jsx`, `AgentRunFlowchart.test.jsx`, `frontend/src/pages/AgentOS.jsx`

**Changes:**
- `.railwayignore` added — trims Railway CLI upload from ~321 MB to ~40 MB by excluding `node_modules`, `.git`, sibling app dirs. Correct, no risk.
- `AgentRunFlowchart.jsx` — dual-shape rendering for v1 trace (`label/detail/at, status:done|running`) and v2 trace (`description/ordinal/step, status:work|completed`). Status color map extended; historical v1 runs still render. Correct.
- `AgentOS.jsx` — Review draft button gating changed from `m.role === "agent"` (role the v2 engine never emits) to `Boolean(run && run.deliverable)`. Fix is correct; the v2 engine writes a single `assistant` message carrying the run + deliverable.

**Critical invariants:** no Python files touched; no `client_id`/`tenant_id` issue applicable.
**Verdict:** ✅ No issues.

---

### 3. `d20284f` — Agent OS phase-3 polish: routing chip, legacy-draft reject, slot extraction (#208)
**Risk:** MEDIUM
**Files:** `backend/routers/os_threads.py`, `backend/routers/os_deliverables.py`, `migrations/132_reject_legacy_os_deliverables.sql`, `agent-service/src/agent-os/agents/booking/agent.ts`, `agent-service/src/agent-os/agents/booking/extract-slot.ts`, `extract-slot.test.ts`, `frontend/src/components/os/AgentRunFlowchart.jsx`, `AgentRunFlowchart.test.jsx`

**Changes:**

**Backend — `os_threads.py` `_attach_routing`:**
- New helper reads `os_routing_decision` + `os_model_call_log` to attach a `routing` object to each run.
- Uses `client_id = claims["tenant_id"]` correctly (JWT claim → `client_id` variable per established pattern). Confirmed no `tenant_id` leak to DB queries — all go through `tenant_table(db, ..., client_id)`.
- Best-effort: `except Exception:` with logger warning; any telemetry failure leaves runs untouched. Not a bare `except:`, so pre-commit hook compliant.
- 2 additional DB queries per `GET /threads/{id}/messages` call, both bounded by `in_("run_id", run_ids)`. Fixed overhead, not N+1.
- No `from __future__ import annotations`. ✅

**Backend — `os_deliverables.py` pending filter:**
- Runtime filter: `if deliverable.get("format") and not deliverable.get("channel"): continue`
- Defensive companion to migration 132; keeps queue v2-only even if legacy worker fires post-cutover.
- No auth surface change, no schema touch. ✅

**Migration 132 — `reject_legacy_os_deliverables.sql`:**
- UPDATE on `os_agent_runs` — flips `deliverable_status` from `pending_approval` → `rejected` for rows with JSONB `format` key and no `channel` key.
- Idempotent, non-destructive (body retained, only status changes).
- Commit message confirms: "Migration 132 applied separately via Supabase MCP." Already live. ✅

**Agent-service — `extract-slot.ts`:**
- New deterministic regex extractor (no LLM call). Returns `undefined` on no match — safe fallback preserved.
- `normalizeDay` strips trailing `s` for plural day names before lookup; acceptable edge handling.
- 6 unit tests cover happy path, abbreviations, day-only, time-only, no-match, undefined input. All pass per commit message (11/11 agent-service tests).
- Low risk: only invoked when `offered_slot` and `requested_day` are both absent. ✅

**Critical invariants check:**
- `from __future__ import annotations`: not present in any modified `.py` file ✅
- `client_id` not `tenant_id` on DB queries: all DB calls use `tenant_table(..., client_id)` ✅
- Bare `except:` blocks: none (`except Exception:` is typed) ✅
- `status` not `lead_stage`: no leads table touched ✅
- Widget JS: not touched ✅

**Verdict:** ✅ No issues. Well-tested, best-effort failure modes in place.

---

## Summary

All 3 commits are clean. No LOW-risk bugs found requiring immediate fix. No MEDIUM/HIGH issues to file.

The Agent OS phase-3 work (routing chip, legacy-draft rejection, slot extraction) is solid:
- Tests pass (38/38 frontend, 11/11 agent-service per commit message)
- Migration is idempotent and already applied
- New DB queries in `_attach_routing` are best-effort and fail gracefully
- `extract-slot.ts` is deterministic (no LLM call), correct fallback behavior

**No fixes committed. No issues filed.**
