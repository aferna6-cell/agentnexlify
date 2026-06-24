# Improvement Backlog — Run 65 (2026-06-24-pm)

Prioritized view as of 2026-06-24. Governance corrections applied this run.

---

## WINNER (run 65)

**Fix Widget Drift + Em-Dash Violations** — AUTONOMOUS-EXECUTABLE, S-effort, CRITICAL
- Unblocks pre-commit Check 13 for all developers
- Same class as runs 49/55/57 — proven nightly delivery channel
- ETA: 1-2 days via nightly review

---

## P0 — Pending (blocking / revenue-critical)

| Item | Run | Age | Status | Notes |
|------|-----|-----|--------|-------|
| AI-to-Human Handoff v1 | 4, 38 | 69d | pending_approval | M-effort, human required. Critical all 7 verticals. Next winner candidate after autonomous queue clears. |

---

## P1 — Next autonomous candidates (moratorium-safe)

| Item | Run | Effort | Status | Notes |
|------|-----|--------|--------|-------|
| Plan-name invariant guard (Check 7) | Bonus B, runs 60-64 | S | parking lot → run 66 candidate | Sequenced after run 65 winner. AUTONOMOUS-EXECUTABLE. |
| email_sequences.py god-class split | 41 | L | pending_approval | god-class-splitter + post-split-test-repair both ready. Next human-required code health item. |

---

## P2 — Standing actions (human sprint required)

| Item | Run | Age | Notes |
|------|-----|-----|-------|
| Wire check_project_invariants.py Check 10 (run 22) | 22 | 38d | pending_autonomous, de-coupled from sprint. Still valid. |
| Widget 3-Copy Sync Guard script | 7 | 61d | pending_autonomous. scripts/check-widget-sync.sh still not created. Run 50 extension still not applied. |
| Extend nightly scope + Item B | 50 | 19d | pending_autonomous. Enables widget sync guard. |

---

## P3 — Parking lot (promote when ready)

| Item | ROI | Notes |
|------|-----|-------|
| Fix GH #263 — 24 pending migrations investigation | 2.3 | Insufficient triage — needs DB audit first |
| Zapier API key plan_status enforcement | 2.5 | GH #107, security, HIGH. Route via issue-to-pr-loop. |
| Cross-tenant isolation test for os_graph_memory | 2.1 | Add after next Agent OS sprint |
| New-table checklist in schema-discipline.md | 2.0 | After next Agent OS service |
| Fix email_sequences N+1 queries | 2.3 | GH #112, simpler post-split |
| Fix kb-autopopulate.sh (35d+ broken) | 1.8 | Replace agent-browser with curl/WebFetch |
| Onboarding V2 characterization tests | 1.7 | Plans/onboarding-v2_plan.md exists |
| California AI companion disclosure audit | 1.6 | SB 243, low-effort compliance check |

---

## Governance state (post-corrections, run 65)

- Moratorium: ACTIVE (true_pending ~5 > max_pending_approvals 2)
- Both mandate items (GH #308, GH #292/#293) implemented 2026-06-23
- Run 65 is first free-choice run in 6 cycles
- Moratorium exit path: ship AI-to-Human Handoff (P0) + email_sequences split (P1) → drops true_pending to ~3-4
- Full moratorium exit: sprint session clearing runs 20/21/29/42/50 (~1h) → drops to ≤2

---

## Governance corrections applied this run

| Item | Old Status | New Status | Reason |
|------|-----------|-----------|--------|
| Run 62 GH #292/#293 | pending_approval | implemented | 57f2bb4d, 29ed1d43 (2026-06-23) |
| Run 59 GH #308 | pending_approval | implemented | 3a958e5f (2026-06-23) |
| Run 30 Billing Constants Tests | pending_approval | moot | test_plan_gating_new_plans.py supersedes; old billing model retired |
| Run 28 Invoke /moratorium-sprint | pending_approval | superseded | All sprint items resolved via other paths |
| Run 35 email_sequences split first | pending_approval | superseded | Run 41 is canonical active_direction |
