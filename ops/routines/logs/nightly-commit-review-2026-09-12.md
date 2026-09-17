# Nightly Commit Review — 2026-09-12

**Window:** last 24h (2026-09-11 → 2026-09-12)
**Commits reviewed:** 6
**LOW:** 4 | **MEDIUM:** 2 | **HIGH:** 0
**Autonomous fixes:** 0
**Issues filed:** 0

---

## Commits

### 865fa35 — subconscious: run 120 — Step 9E credential expiry escalation
**Risk: LOW**
Files: `subconscious/runs/2026-09-11-pm/*`, `subconscious/state/governance.json`, `subconscious/state/memory.jsonl`
Subconscious routine output. No production code. No issues.

---

### adb31f9 — fix(agent-os): surface send_email approval failure outcomes (#844)
**Risk: MEDIUM**
Files: `backend/routers/os_tool_executions.py` (+25 lines), `tests/test_send_email_approval_http_contract.py` (+149 lines)

Router now surfaces two new failure paths:
- `outcome.get("unknown")` → HTTP 502 `send_outcome_unknown`
- `outcome.get("failed")` → HTTP 502 (or provider status if 400–599) `gmail_api_error`

Code review: clean. `record_execution_outcome` signature matches. No `__future__` annotations. Tests cover both branches. Status code cast `int(provider_status)` is redundant (already int) but harmless. No bugs found.

---

### 3326f45 — subconscious: run 2026-09-11 — Step 9E credential expiry escalation
**Risk: LOW**
Files: `subconscious/runs/2026-09-11/*`, `subconscious/state/governance.json`, `subconscious/state/memory.jsonl`
Subconscious routine output. No issues.

---

### 8ab46d5 — ops: morning-digest 2026-09-11
**Risk: LOW**
Files: `ops/routines/logs/morning-digest-2026-09-11.md`
Ops log only. No issues.

---

### 0605d0f — fix(agent-os): terminalize deterministic Gmail send failures (#841)
**Risk: MEDIUM**
Files: `backend/services/os_tools.py` (+43 lines), `tests/test_gmail_known_failure_terminalization.py` (+105 lines)

Adds `KnownGmailSendFailure` exception. `GmailMailboxPort.send` now raises it when provider returns a status code on failure. `_run_data_plane_tool` wrapper catches it, calls `svc.record_execution_outcome` to mark execution terminal, returns structured dict with `failed=True` and `status_code`.

Code review: exception propagation path correct (`KnownGmailSendFailure` defined in `os_tools.py`, raised in `GmailMailboxPort.send`, passes through `svc._run_data_plane_tool` uncaught, caught by `os_tools._run_data_plane_tool`). `svc.record_execution_outcome` signature `(db, client_id, execution)` matches call. No `__future__` annotations. Tests included. No bugs found.

---

### c23ebff — docs(nightly): review 2026-09-11 [auto-nightly]
**Risk: LOW**
Files: `docs/dev-knowledge/nightly-reviews/2026-09-11.md`, `ops/routines/logs/nightly-commit-review-2026-09-11.md`
Previous nightly review log. No issues.

---

## Result
No LOW-risk bugs found. Two MEDIUM commits reviewed — logic correct, tests present. No action required.
