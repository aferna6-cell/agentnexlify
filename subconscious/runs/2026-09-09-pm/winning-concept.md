# Winning Concept — 2026-09-09-pm

## Recommendation
Split `backend/services/os_tool_executions.py` (783L, 30+ functions, 4 distinct concerns) into 4 focused modules, each under 250L.

## Why This, Why Now
`os_tool_executions.py` crossed the 600L Rule 9 threshold long ago (783L) and has been stable for 10+ days — the lowest-risk window for a split. The governance mandate for run 118 explicitly requires this recommendation when Step 9L is confirmed (grep=2 ✓) and the file is 10+ days stable. Four clearly distinct concern groups are already visible in the function list: tool lifecycle CRUD, lead/note writes, email validation, and data-plane dispatch — clean seams with no cross-cutting calls observed. Splitting now reduces per-change blast radius from 783L to <250L per module, makes parallel agent work conflict-free, and brings the file into Rule 9 compliance before the agent_os sprint adds more functions.

## Implementation Sketch
1. **Blast radius scan first**: run `gitnexus_impact({target: "os_tool_executions", direction: "upstream"})` to enumerate all callers and their import patterns.
2. **Create `os_tool_lifecycle.py`** (~250L): `to_row`, `_now`, `_int_or`, `find_by_idempotency_key`, `_normalized_idempotency_key`, `_is_fail_closed`, `_requires_idempotency_key`, `persist_tool_executions`, `_recover_duplicate_inserts`, `claim_for_execution`, `claim_if_input_valid`, `record_execution_outcome`, `mark_engine_unavailable`, `apply_unknown_send_outcome`, `rfc822_msgid_for`, `DuplicateInsertError`, `EngineUnavailableError`.
3. **Create `os_tool_lead_actions.py`** (~80L): `apply_customer_notes`, `_append_lead_note`, `_mark_note_execution_unverified`.
4. **Create `os_tool_email.py`** (~120L): `_normalize_email`, `email_recipient_from_input`, `requires_preclaim_email_check`, `input_passes_python_email_gate`, `validate_before_claim`.
5. **Create `os_tool_data_plane.py`** (~200L): `propose_tool_execution`, `list_tool_executions`, `get_tool_execution`, `present_tool_execution`, `_run_data_plane_tool`.
6. **Update `os_tool_executions.py`** to re-export everything from the 4 new modules — keeps all existing callers working without changes during the migration window. One import per new module, then `__all__` if needed.
7. **Update direct callers** (from gitnexus scan) to import from new module paths rather than the shim, per Rule 8 (no half-migrations) — do ALL callers in the same PR.
8. **Run existing tests** to confirm no regressions. Add one import-path smoke test.
9. **Commit with `[skip ci]` note** if callers span frontend-related services, otherwise standard CI.

## What This Replaces
Previous active direction was Step 9L (AI metering coverage nightly check) — now confirmed implemented (grep=2). Step 9L transitions to "monitoring" phase; no further subconscious action needed unless violations start appearing in nightly logs.

## Confidence
**HIGH** — Both governance mandate conditions met: Step 9L confirmed (grep=2) AND os_tool_executions.py 10+ days stable. Debate survived 3-round challenge. Concern groups visible from function list alone; no architectural ambiguity. Precedent: SettingsPage.jsx split (run 14 mandate) succeeded. Subconscious recommends; human approves before execution.
