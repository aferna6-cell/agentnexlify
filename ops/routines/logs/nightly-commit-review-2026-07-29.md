# Nightly Commit Review — 2026-07-29

**Window:** last 24 hours  
**Commits reviewed:** 3  
**LOW-risk bugs fixed:** 0  
**MEDIUM/HIGH issues filed:** 0  
**Overall health:** CLEAN

---

## Commit Triage

### LOW — `a72d14b` ops: nightly-commit-review 2026-07-28 [auto-nightly]
Previous nightly review log. No code.

### LOW — `5288933` ops: morning-digest 2026-07-28
Morning digest log. No code.

### MEDIUM — `8e78f5b` feat(autonomy): sweep runs a crash stranded in 'running' (#608)

**Files changed:** 5 files, 512 lines added (all new)

- `scripts/autonomy/sweeper.py` (152 lines) — `find_stranded()` scans state dir for RUNNING runs quiet >1h; `sweep()` resolves them to FAILED with reason, atomically via `FileCheckpointer`. Never executes a node.
- `scripts/autonomy/loop_graph.py` (+13 lines) — `REENTERABLE_NODES` / `NON_REENTERABLE_NODES` frozensets. Classification enforced by test (test_every_loop_node_is_explicitly_classified).
- `scripts/autonomy/run_loop.py` (+85 lines) — `run_loop list` and `run_loop sweep [--dry-run]` CLI subcommands. Both use `asyncio.to_thread()` to avoid nesting event loops inside the async CLI.
- `scripts/autonomy/ROUTINE.md` (+11 lines) — Runbook updated with sweep commands + new guardrail row.
- `backend/tests/test_autonomy_sweeper.py` (251 lines) — 15 new tests covering stranded detection, sweep resolution, TOCTOU guard, dry-run, awaiting_input exemption, and safe_to_retry logic.

**Triage rationale:** MEDIUM — new autonomy infrastructure, not auth/payments/tenant isolation. Additive only. Closes a real incident (run `a82c9f38` was a permanent corpse after container restart).

**Code quality review:**
- Design is sound: sweeper never executes nodes, only marks state. Side-effect-safe by construction.
- `asyncio.to_thread()` wrapping is correct — `_load()` uses `asyncio.run()` internally (sync function driving async checkpointer), which would nest if called directly from async context.
- TOCTOU guard in `sweep()`: re-loads and re-checks status between `find_stranded` and write. Correct.
- Empty frontier → `safe_to_retry=True`: documented as conservative default (no nodes to check = no blockers).
- `awaiting_input` runs explicitly exempt regardless of age: correct (interrupt mechanism should survive).
- Author-verified: 422 tests passed; 15 new; local CI gate PASS (16 required).

**No bugs found. No issues filed.**

---

## Critical Rules Check

| Rule | Status |
|------|--------|
| `client_id` not `tenant_id` on leads/conversations | PASS — no leads/conversations touched |
| `status` not `lead_stage` | PASS — no lead status changes |
| `areas_of_interest` not `service_interest` | PASS — no leads changes |
| No `from __future__ import annotations` in FastAPI files | PASS — new files are scripts, not FastAPI |
| Widget JS byte-identical | PASS — no widget changes |
| Secrets not in commits | PASS — no secrets detected |
| Schema changes via migration files only | PASS — no schema changes |

Static rule scan: PASS (no `__future__` annotations, no `lead_stage`, no `service_interest` in sweeper.py).

---

## Summary

Quiet night. Two ops logs (LOW) and one MEDIUM autonomy infrastructure commit. The sweeper is a clean, well-tested fix for the crash-stranded-run incident (#605) — additive, non-destructive, and properly gated by re-enterability classification. No bugs. No issues to file.
