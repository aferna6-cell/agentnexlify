# Nightly Commit Review — 2026-07-28

**Window:** last 24 hours  
**Commits reviewed:** 7  
**LOW-risk bugs fixed:** 0  
**MEDIUM/HIGH issues filed:** 0  
**Overall health:** CLEAN

---

## Commit Triage

### LOW — `2f5c28c` ops: nightly-commit-review 2026-07-27 [auto-nightly]
Ops log from previous nightly run. No code.

### LOW — `e9701aa` ops: morning-digest 2026-07-27
Morning digest log. No code.

### LOW — `2cdd2da` chore: weekly skill discovery report 2026-07-27
Docs only — `docs/skill-discovery/2026-07-27.md`. No code changes.

### LOW — `d64a5e4` fix(autonomy): stop the open_pr handoff contradicting the merge node (#603)
Single file: `scripts/autonomy/loop_graph.py` (3 lines changed). Rewrites instruction
text in `_open_pr()` to accurately say merge is handled by the next node, not prohibited
entirely. The old wording said "Do NOT merge" which contradicted the `merge` node that
runs immediately after. No logic change — wording only. Verified by author:
`pytest -k "autonomy or graph" — 407 passed`.  
**No issues.**

### LOW → MEDIUM — `6e032f8` fix(routes): version-stable route introspection (#265) (#600)
- New file `backend/route_introspection.py` (87 lines) — version-stable `iter_routes`,
  `route_paths`, `route_signatures`, `count_routes`. Uses `getattr` for framework
  introspection only; no user input path; no security surface.
- Migrates 6 call sites (5 smoke tests + `scripts/managed_agents/preflight.py`) away
  from walking `app.routes` directly. Fixes a measurement artifact that looked like
  "zero routes" on FastAPI 0.136+.
- `fastapi<0.136` cap deliberately NOT lifted — gated on `c624700` suite first.
- Verified on both FastAPI 0.135.4 and 0.140.7: 60 tests pass, `route_signatures = 623`
  on both. **No issues.**

### MEDIUM — `c624700` test(router): pin router-composition semantics ahead of the fastapi bump (#602)
- New file `backend/tests/test_router_composition_semantics.py` (405 lines, 13 tests).
- Pins four router behaviors that must hold before `fastapi<0.136` cap can lift:
  middleware ordering across `include_router`, `dependencies=` inheritance and ordering,
  `prefix=` composition, mounted sub-app resolution.
- **Notable finding in commit:** "parent HTTP middleware DOES wrap requests into a mounted
  sub-app. If a bump moved user middleware below routing, auth/tenant scoping would stop
  covering mounts silently. Now a test failure instead." — this finding is now protected
  by a characterization test. No current bug; future bump is now gated.
- `requirements.txt` comment corrected from "proven incompatible" to "UNVERIFIED" — accurate.
- Verified: CI local PASS (16 gates). **No issues. Test coverage is the right response.**

### MEDIUM — `d7259d4` feat(graph): agent graph runtime + autonomous engineering loop (#599)
Large additive commit (43 files, ~10,839 lines). Key facts:
- **Additive only.** No existing module imports `backend/graph/` or `scripts/autonomy/`.
- **Migration 189 not applied.** `graph_runs` / `graph_run_steps` tables exist as SQL file
  only — no database changes landed.
- **No Routine armed.** The autonomous loop is not executing.
- `tenant_id` on graph tables is intentional and documented in migration 189 comments:
  follows `automation_*` family convention. Not a schema-discipline violation.
- No `from __future__ import annotations` in any graph file. No bare-except blocks.
- `_merge` node in `loop_graph.py` can auto-merge PRs when all gates pass. Commit message
  notes this is "owner-granted (2026-07-28)" and capped at 4/day to avoid Vercel deploy
  limit. **Flag for awareness: autonomous merge capability is now in the codebase.**
- Author-verified: `scripts/ci_local.sh PASS (16 required gates)`, backend suite
  `3068 passed / 35 skipped / 0 failed`.
- **No bugs found. Awareness note only (see below).**

---

## Awareness Notes (no action required, no issue filed)

**Autonomous merge capability now in codebase (not yet armed)**  
`scripts/autonomy/loop_graph.py::_merge` will auto-merge PRs when:
- All CI gates green
- PR is not a draft
- Loop has not exceeded 4 merges/day

This node is not connected to any active Routine. When the owner arms a cloud Routine
per `scripts/autonomy/ROUTINE.md`, merges will happen without per-PR human approval.
No action required now — flagging so the owner is aware before arming.

---

## Critical Rules Check

| Rule | Status |
|------|--------|
| `client_id` not `tenant_id` on leads/conversations | PASS — graph uses tenant_id correctly for automation layer |
| `status` not `lead_stage` | PASS — no lead status changes |
| `areas_of_interest` not `service_interest` | PASS — no leads changes |
| No `from __future__ import annotations` in FastAPI files | PASS — none found in new code |
| Widget JS byte-identical | PASS — no widget changes |
| Secrets not in commits | PASS — no secrets detected |
| Schema changes via migration files only | PASS — migration 189 is file-only, not applied |

---

## Summary

Clean night. Three infrastructure/ops additions (daily logs, skill report), one autonomy
wording fix, one route introspection fix, one middleware-ordering test suite, and one large
additive graph runtime (not yet activated). No bugs. No MEDIUM/HIGH issues to file.

Autonomous merge capability landed in the codebase but is not yet armed — owner should
be aware before connecting a Routine.
