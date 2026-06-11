# Improvement Backlog — 2026-06-11-pm

## Active
- Fix `check_project_invariants.py` false positive (1-line anchor fix, human ~2 min) + nightly fixes 10 JSX em-dash violations → Check 10 auto-wires tonight.

## Parking Lot (survived debate but not chosen)
- **Widget sync guard human-execute** — create `scripts/check-widget-sync.sh` + wire into pre-push + fix CLAUDE.md Invariant #4. Run 50 autonomous directive failed to fire (6 days). Widget copies currently in sync but unguarded. ~10 min. Include as Bonus Action B.
- **Cross-tenant isolation test for os_graph_memory** (ROI 2.1) — 2 mock-based tests: accumulate_from_turn(client_id=A) → graph_kb_entries(client_id=B) → empty. AUTONOMOUS-EXECUTABLE. Deferred until next Agent OS sprint.
- **Fix kb-autopopulate.sh** (ROI 1.8) — 35+ days broken, agent-browser CLI not installed. Replace with curl/requests calls. AUTONOMOUS-EXECUTABLE. KB quality degrading but 114 articles still available.
- **Add tenant scope registration checklist to schema-discipline.md** (ROI 2.0) — 3rd occurrence of `_TENANT_COLUMN_OVERRIDES` miss (run 54). 5-question new table checklist. Promote when next Agent OS service added.

## Rejected This Run
- **Fix GH #181 AMOUNT_TO_PLAN** — KILLED. `rejected_paths` governance rule holds (5-run threshold exceeded, condition (b) not met). PR #228 confirmed path but didn't change mechanism. Remains `critical_standing_action`.

## Questions for Next Run
- Was the `check_project_invariants.py` false-positive fix applied by human? (grep `channels_instagram.py` — if `__future__` check passes without actual import, fix is done)
- Did nightly fix the 10 JSX em-dash violations? (check_project_invariants.py exit code — should be 0)
- Did Item A (Check 10) auto-wire in the same nightly cycle? (grep scripts/hooks/pre-commit for check_project_invariants)
- Was PR #183 merged? (GH #181 billing fix)
- Was check-widget-sync.sh created? (Bonus Action B)
- What new features shipped in the next sprint? (watch for new em-dash violations — Check 10 wire would catch them)
