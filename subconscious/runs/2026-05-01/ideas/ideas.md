# Ideas — Run 12 (2026-05-01)

## Context

- **Moratorium active**: 4 pending approvals (runs 3, 4, 7, 8). Lifts at ≤3.
- **Oldest pending**: Run 3 — JS Silent Catch Guard (2026-04-11, day 23+).
- **Key new findings this run**:
  - Nightly review 2026-05-01 issued Issue #109 (AdminAnalyticsPage silent catch) + Issue #110 (golden eval harness CI).
  - Em-dash blocker for run 8 NOT cleared — nightly review was wrong. `check_project_invariants.py` fails on 9 em-dash violations: WizardStepAutoKB.jsx:2/140/172/254 AND AutomationActivityCard.jsx:156/172/188/251/389 (new, from 90ba1c5 slice-3 UI commit).
  - Pre-commit has 9 existing checks (Check 9 = "dropped conversations.messages"). JS silent catch guard would be Check 10.
- **Onboarding V2 sprint**: 21 issues, starting now. More JSX files incoming.

---

### Idea 1: JS Silent Catch Guard — Fix AdminAnalyticsPage + Add Check 10 to pre-commit
**Evidence:** Run 3 winner (2026-04-11, day 23+). AdminAnalyticsPage.jsx:117-122 has 6 `.catch(() => null)` in Promise.all, zero logging. Issue #109 opened by nightly review 2026-05-01. Pre-commit has 9 checks; JS silent catch would be Check 10 (not 9 as previously cited — existing Check 9 is "dropped conversations.messages"). Pattern migrates to new files each week without a guard.
**Action:** Fix AdminAnalyticsPage.jsx:117-122 (6 calls → `console.warn` pattern); add Check 10 to `scripts/hooks/pre-commit` blocking `.catch(() => null/{})`; escape hatch `// ok-silent-catch` for intentional graceful degradation.
**Impact:** Prevents silent-catch pattern from spreading into 21 onboarding V2 files. Closes oldest moratorium item. Lifts moratorium if one other is implemented concurrently.
**Category:** code_health

---

### Idea 2: Scope em-dash check + Wire check_project_invariants.py (Run 8 Unblocking)
**Evidence:** Run 8 winner (2026-04-25). `check_project_invariants.py` FAILS on 9 em-dash violations: WizardStepAutoKB.jsx + AutomationActivityCard.jsx (5 new from slice-3 UI commit 90ba1c5). The "—" characters are legitimate UI display characters in JSX (table empty-state rendering), not content/copy errors. Nightly review incorrectly reported em-dash as stale — direct script run proves violations still exist. Em-dash check scoped too broadly (all HTML/JSX, should be content/markdown only).
**Action:** Update `check_project_invariants.py` em-dash check to skip `.jsx` files and `/*.md` files outside `/copy/` directory; then wire script into `scripts/hooks/pre-commit` as Check 11.
**Impact:** Closes run 8 winner. Pre-commit gains schema/naming invariant enforcement (client_id, status, areas_of_interest). Reduces 4 pending → 3 → moratorium lifts.
**Category:** code_health

---

### Idea 3: Wire Golden Eval Harness to CI (Issue #110)
**Evidence:** `backend/tests/evals/test_lead_qualifier_golden.py` added in `7854ede` (2026-04-30). Issue #110 opened by nightly review 2026-05-01. Gated behind `RUN_LEAD_QUALIFIER_EVAL=1` env var — CI never sets it. Parking lot ROI 2.5 (highest). Onboarding V2 sprint will touch lead qualifier flow. Golden JSON has 25 test cases.
**Action:** Add `.github/workflows/lead-qualifier-eval.yml` with Monday 08:00 UTC cron + `workflow_dispatch`; set `RUN_LEAD_QUALIFIER_EVAL=1` in CI; require `LEAD_QUALIFIER_AGENT_ID` in GH Secrets (provision note in implementation sketch); 80% pass threshold.
**Impact:** Qualifier regressions caught weekly before they reach prod. First eval gate in CI. Closes Issue #110.
**Category:** operational / code_health

---

### Idea 4: Onboarding V2 Characterization Tests (Before Sprint Start)
**Evidence:** `plans/onboarding-v2_plan.md` (37c151c) lists 21 issues, sprint starting. `widget_helpers.py` split (run 5) was implemented without tests — still `implemented_unverified` after 13 days. Same syndrome prevented from repeating. `backend/tests/` has established FastAPI test patterns (test_managed_agents.py, test_widget_chat.py).
**Action:** Write `backend/tests/test_onboarding_characterization.py` covering: `POST /api/onboarding/start`, `POST /api/onboarding/complete_step`, `GET /api/onboarding/wizard_state`. Three happy-path + one error-path test per endpoint.
**Impact:** Sprint starts TDD-compliant. Prevents implemented_unverified syndrome for 21-issue sprint.
**Category:** code_health

---

### Idea 5: Widget 3-Copy Sync Guard (Run 7)
**Evidence:** Run 7 winner (2026-04-24). Pre-push has widget check at line 218 but `scripts/check-widget-sync.sh` doesn't exist. CLAUDE.md Invariant #4 still says "2 widget paths" when 3 exist (`widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`). `b34e687` (nightly 2026-05-01) added `.gitignore` changes but no widget sync script.
**Action:** Create `scripts/check-widget-sync.sh` (3-way md5 check); update CLAUDE.md Invariant #4 text; wire into pre-push as a FAIL gate.
**Impact:** Prevents widget embed breakage from copy drift. Closes run 7.
**Category:** code_health

---

## ROI Ranking (moratorium context)

| Rank | Idea | Moratorium Age | Est. LOC | Blockers |
|------|------|---------------|----------|----------|
| 1 | JS Silent Catch Guard (run 3) | Day 23+ | ~25 | None |
| 2 | Scope em-dash + Wire invariants.py (run 8) | Day 6 | ~15 | em-dash scope fix first |
| 3 | Wire golden eval harness (parking lot) | — | ~25 | GH Secret needed |
| 4 | Onboarding V2 char tests (parking lot) | — | ~80 | None |
| 5 | Widget 3-copy sync guard (run 7) | Day 7 | ~30 | None |
