# Ideas — Run 42 (2026-05-30-pm)

## Evidence Summary

email_sequences.py = 1255L confirmed unchanged. All prerequisites met as of d481799 (2026-05-30 nightly):
god-class-splitter SKILL.md (e848b87) + post-split-test-repair SKILL.md (d481799). GH #181 still broken:
billing.py:263 AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional; test_billing_amount_to_plan.py:40-44
backwards assertions certify broken state; Check 11 fires WARNING on every commit as live reminder.
Moratorium Items A/B/D ALL MISSING: check_project_invariants not in pre-commit, check-widget-sync.sh absent,
lead-qualifier-eval.yml absent. GH #193 created by nightly 2026-05-30 — moratorium escalation (44d oldest,
13 pending) now publicly visible in GitHub. auth.py = 1591L (largest router, bigger than email_sequences).
Human present in interactive session — highest-probability execution window.

---

### Idea 1: Invoke /god-class-splitter on email_sequences.py — Human Present in Interactive Session
**Evidence:** email_sequences.py 1255L confirmed. All tooling ready: god-class-splitter SKILL.md (e848b87) + post-split-test-repair SKILL.md (d481799, yesterday). Run 35 active_direction (since 2026-05-26-pm). Prerequisites cleared 24h ago — run 41 was the first full-cycle recommendation after unblocking. Human actively running /subconscious interactively — highest-probability execution window in 27+ days.
**Action:** In this interactive session: (1) Fix GH #181 first (~15 min), (2) Invoke /god-class-splitter on backend/routers/email_sequences.py (~2h), (3) Run /post-split-test-repair checklist.
**Impact:** Resolves run 35+41 active_direction (2 pending → 0 for this item). Enables GH #112/#113 N+1 fixes to be scoped to single modules. Sets production template for remaining 8 god-class files (auth.py 1591L being next).
**Category:** code_health

---

### Idea 2: Label moratorium Item A (check_project_invariants pre-commit) as AUTONOMOUS-EXECUTABLE
**Evidence:** 061582c (nightly 2026-05-29) added Check 11 — a 22-line bash block to scripts/hooks/pre-commit — autonomously without human instruction. Item A is simpler: 3 lines calling existing `python scripts/check_project_invariants.py`. Script confirmed passing all 6 checks (em-dash blocker cleared 8f680e8). Moratorium day 27+. GH #193 escalation created today.
**Action:** Write Item A specification in current run artifacts with AUTONOMOUS-EXECUTABLE label. Nightly pickup tonight.
**Impact:** Nightly executes Item A tonight → pre-commit gains invariant checking (client_id, status, areas_of_interest) on every commit. Zero human time. Reduces pending by 1.
**Category:** workflow

---

### Idea 3: Plan auth.py god-class split — next largest target after email_sequences
**Evidence:** auth.py = 1591L — LARGEST router file, exceeds email_sequences (1255L). god-class-refactor_plan.md includes auth.py. PR #180 proved split+repair workflow. email_sequences split (if done today) provides production template for next god-class target.
**Action:** After email_sequences split, create split plan for auth.py into auth_core + auth_sessions + auth_token modules.
**Impact:** Reduces largest security-critical god-class. Isolates JWT/session logic for easier testing and rotation.
**Category:** code_health

---

### Idea 4: Label moratorium Item D (lead-qualifier-eval.yml) as AUTONOMOUS-EXECUTABLE
**Evidence:** .github/workflows/lead-qualifier-eval.yml MISSING confirmed. Nightly creates new files autonomously (SKILL.md confirmed, ccf0c8e confirmed). New CI YAML = additive new file, same class as SKILL.md creation. backend/tests/evals/test_lead_qualifier_golden.py passes locally (confirmed run 14). GH issue #110 tracked 25+ days. No existing CI workflow for lead qualifier regression.
**Action:** Write lead-qualifier-eval.yml spec in current run artifacts with AUTONOMOUS-EXECUTABLE label.
**Impact:** Closes GH #110. Monday cron + PR trigger catches lead qualifier regressions. Item D of moratorium sprint.
**Category:** operational

---

### Idea 5: Create check-widget-sync.sh as AUTONOMOUS-EXECUTABLE for nightly execution
**Evidence:** scripts/check-widget-sync.sh MISSING since run 7 (2026-04-24, 36+ days). All 3 widget copies in sync as of latest nightly PASS. Creating a new bash script = additive new file (same class as SKILL.md creation). CLAUDE.md Invariant #4 still says "2 copies" when there are 3.
**Action:** Write check-widget-sync.sh spec as AUTONOMOUS-EXECUTABLE in current run artifacts.
**Impact:** Item B of moratorium sprint. Protects 3-way widget sync going forward (widget/ + frontend/public/widget/ + landing-page-v2/widget/).
**Category:** code_health
