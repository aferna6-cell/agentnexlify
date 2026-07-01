# Idea 4: Plan-Name Guard Check 7 (Pre-commit Invariant)

**Evidence:** Parked since run 73. `check_project_invariants.py` has 6 checks but no plan-name validator. CLAUDE.md §"Plan names + prices" lists canonical names: `chatbot`, `agent_os`, `free`, plus legacy `growth`, `autopilot`, `professional`, `enterprise`. Retired names `foundation` and `operations` must never appear. Billing repricing 2026-06-16 makes stale plan names a real drift risk. run 62 winner (GH #292/#293) fixed plan-name bugs in 2 files — systemic guard would prevent recurrence.

**Action:** Add Check 7 to `scripts/check_project_invariants.py`: grep `backend/**/*.py` for retired plan names (`foundation`, `operations`) → FAIL. Grep for legacy names not in billing constants → WARN. ~20 lines Python. S-effort. Not AUTONOMOUS-EXECUTABLE (Python script edits outside nightly scope per Step 9B).

**Impact:** Prevents future plan-name drift. Closes gap that caused GH #292/#293. Deterministic guard vs recurring LLM mistake.

**Category:** code_health

**Concern:** Not autonomous — requires human commit. Lower leverage than Zapier fix. Moratorium adds to human queue.
