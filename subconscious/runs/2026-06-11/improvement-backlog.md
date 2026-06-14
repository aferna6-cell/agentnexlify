# Improvement Backlog — 2026-06-11

## Active

- Fix `channels_instagram.py` `from __future__ import annotations` + clear 10 em-dash violations → exits 0 → Check 10 auto-wires tonight (run 55 winner, AUTONOMOUS-EXECUTABLE)

## Parking Lot (survived debate but not chosen)

- **Wire Check 10 in WARNING mode** (Idea 2, WEAKENED): Contradicts Item A design (FAIL mode) and doesn't solve hooks-not-installed root cause. Valid if Item A keeps failing, but try the FAIL path first.
- **Create check-widget-sync.sh** (Idea 4, pending_autonomous since run 7 / day 50+): AUTONOMOUS-EXECUTABLE via nightly. SKILL.md run 50 scope extension covers this. Promote to interactive winner if nightly still hasn't executed after run 56.
- **Home.jsx split** (Idea 5, 1171L god-class): HUMAN-REQUIRED, 1-2h task via `/god-class-splitter`. Schedule after moratorium exit sprint.
- **Tenant scope checklist in schema-discipline.md** (run 54 parking lot, ROI 2.0): Append 5-question New Table Checklist; promotes when next Agent OS service is added.
- **Cross-tenant isolation test for os_graph_memory** (run 54 parking lot, ROI 2.1): 2 tests verifying client_id isolation. Deferred until next Agent OS sprint.
- **Fix kb-autopopulate.sh** (run 54 parking lot, ROI 1.8): agent-browser CLI not installed. Replace with curl/WebFetch. Restores twice-daily KB auto-population.
- **Fix GH #181** (billing.py AMOUNT_TO_PLAN missing 15000/25000): critical_standing_action; in rejected_paths as winner; manual ~15 min. Fastest path: merge PR #183.
- **email_sequences.py / email_sequences.py god-class split** (run 41, 1255L): unblocked once GH #181 resolved.

## Rejected This Run

- **Idea 2: Wire Check 10 in WARNING mode** — KILLED as primary winner. Contradicts Item A FAIL-mode design. Root cause is hooks-not-installed, not FAIL vs WARNING. Better path: Idea 1 + Idea 3 restore exits 0 → auto-wire as FAIL per original design.

## Questions for Next Run

1. Did tonight's nightly successfully wire Check 10 after this run's commit restores exits 0?
2. Has Item B (check-widget-sync.sh) executed in the nightly cycle yet? If not after run 56, promote to winner.
3. Were any new `from __future__ import annotations` violations introduced in new router files? If so, consider extending Check 2 to services/ as well.
4. Has PR #183 been merged? If still open at run 56, reconsider as winner (condition b for rejected_paths: new framing + PR exists).
