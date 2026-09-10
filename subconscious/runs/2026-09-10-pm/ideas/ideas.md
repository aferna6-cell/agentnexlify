# Ideas — Run 118 (2026-09-10-pm)

## Context
Run 118. Governance mandated autonomous-executable escalation for Step 9L at this run (3rd carry-forward per precedent: Steps 9F/9G/9I/9J/9K all escalated at 3rd carry-forward). Key governance correction: Step 9L IS already in the SKILL.md (grep confirmed 2 hits in functional block lines 457/471). Governance.json still shows `implemented: false` — needs correction.

---

### Idea 1: Fix check_ai_metering.py exit code (RC 0 when violations found should be RC 2)
**Evidence:** `scripts/check_ai_metering.py` outputs 45 violations and exits with code 0. Step 9L SKILL.md block at line 457 explicitly checks: `STEP9L_RC == 0 → log PASS/continue` and `STEP9L_RC == 2 → violations found → file issues`. Current behavior: nightly Step 9L runs, sees RC=0, logs "Step 9L: PASS — 0 violations" and never files any GH issues. Silent failure. 45 real billing violations go untracked every night. GH #827 (P1, 45 unguarded AI call sites) was filed manually — without the fix, Step 9L never files the per-function issues that feed the issue-to-pr-loop.
**Action:** Edit `scripts/check_ai_metering.py` main function: when violations list is non-empty, exit with `sys.exit(2)`. When clean, exit with `sys.exit(0)`. Update the script's docstring/exit-codes section to document the contract.
**Impact:** Step 9L fires correctly on next nightly run. All 45 unguarded AI-calling functions get individual GH issues filed with labels `billing+ai-ready`. Issue-to-pr-loop can pick them up when GH #399 resolved. Every future new AI route gets caught within 24h.
**Category:** code_health

---

### Idea 2: Split os_tool_executions.py god class (783 lines, threshold 600)
**Evidence:** `backend/services/os_tool_executions.py` is 783 lines. User Rule 9: "if a file is already >600 lines and I'm about to add more, stop. Factor the existing code into modules first." File stable 8+ days (last commit f22ef04, ~2026-08-30). os_workflows module is actively being developed (planner_bakeoff.py, M8 features, run_live_bakeoff.py). GH #801 P0 is in this module. More code is imminent. Splitting now is easier than at 1000+ lines.
**Action:** Recommend split into: `tool_registry.py` (manifest/discovery), `tool_runner.py` (execution lifecycle), `tool_validators.py` (input validation), `tool_results.py` (result formatting). Update imports across `os_workflows/` and `backend/routers/os_tool_executions.py` (411L).
**Impact:** Smaller blast radius per change. GH #801 easier to diagnose with isolated execution lifecycle. Future M8 features land in focused files. Prevents 1200L god class in 2 sprints.
**Category:** code_health

---

### Idea 3: Fix Step 9J token budget — Dependabot PRs processed in batches with state file
**Evidence:** Runs 115/116/117 all show "17/19 Dependabot PRs skipped due to token budget." 2 PRs processed per nightly, 17 always skipped. CVE window stays open for the 17 unprocessed. The 19 open Dependabot PRs include security patches. Step 9J rebase trigger works for the 2 it processes but doesn't scale.
**Action:** Add `subconscious/state/step9j-cursor.json` tracking last processed PR index. Step 9J reads cursor, processes next 5 PRs from the 19 (not 2), updates cursor. Full sweep in 4 nightly runs.
**Impact:** All 19 Dependabot PRs processed within 4 nights. CVE window closes within a week. Rebase triggers reach all PRs.
**Category:** workflow

---

### Idea 4: Diagnose P0 GH #801 (approve_send_once execution leak) and add ai-ready label
**Evidence:** Morning digest 2026-09-10 flags GH #801 as P0, risk:high: "approve_send_once leaves execution running with no provider messageId." No recent commits touching it. No PR linked. No comments since filing. Agent OS feature work is blocked. Issue-to-pr-loop can't pick it up without ai-ready label and a root cause sketch.
**Action:** Read `backend/services/os_workflows/engine.py` (and approve_send_once), write root cause analysis, post diagnostic comment to GH #801 with proposed minimal fix (bounded retry on messageId, timeout after N attempts), add `ai-ready` label.
**Impact:** P0 gets queued for autonomous resolution when GH #399 (AUTOPILOT_GH_TOKEN) is resolved. Unblocks agent-os feature development. Prevents silent execution leak from running indefinitely.
**Category:** customer_value

---

### Idea 5: Step 9M — Auto-cleanup remaining `__future__` annotations in test files
**Evidence:** CI guard (PR #834, `scripts/check_backend_future_annotations.py`) now blocks new violations. 3 test files remain in baseline (GH #823): `test_website_connect.py`, `test_local_seo_handlers.py`, `test_os_invoice_e2e.py`. These are safe to remove (test files, not FastAPI route handlers). Human is 2/5 of the way through the sprint. Nightly could close this automatically.
**Action:** Add Step 9M to nightly-commit-review SKILL.md: read `scripts/check_backend_future_annotations.py` baseline, for each file in baseline that contains `from __future__ import annotations` in a test file (path starts with `backend/tests/`), remove the import, run `python3 scripts/check_backend_future_annotations.py`, commit if green. Cap at 1 file per nightly run.
**Impact:** GH #823 closes automatically within 3 nightly runs. CI baseline shrinks to 0. Frees human sprint attention for P0/P1 items.
**Category:** workflow
