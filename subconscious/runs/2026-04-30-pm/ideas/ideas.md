# Ideas — 2026-04-30-pm (Run 11)

## Evidence Digest

**Commits (3 days):** Agent filter skill + lead qualifier golden eval harness (812 lines, `7854ede`). Attribution service extended with dollars/hours slice 2. Dashboard activity feed UI. Onboarding V2 plan (21 issues, 409-line plan). Friday-reading automation. Bug patterns at 2,320 lines.

**KEY GOVERNANCE CORRECTION:** MarketingDashboardPage.jsx:96 + LocalSEOPage.jsx:262 violations — FIXED by `e68677a` (7 days ago, `fix(silent-errors): add logging to 4 bare-exception/silent-catch handlers`). Violations replaced with `(err) => { console.warn(...); return null; }`. Original run 3 evidence sites no longer violate.

**NEW VIOLATION CLUSTER:** AdminAnalyticsPage.jsx:117-122 — 6 `.catch(() => null)` with ZERO logging in `Promise.all`. Admin dashboard silently loses overview, weekly growth, monthly growth, plan distribution, revenue trends, industry breakdown data.

**NEW EVAL HARNESS:** `backend/tests/evals/test_lead_qualifier_golden.py` + `lead_qualifier_golden.json` added today. Proper env-var gate, 80% pass threshold. NOT wired to CI or any schedule.

**SPRINT RISK:** `plans/onboarding-v2_plan.md` creates 21 issues. Major sprint starting with no JS silent catch guard and no eval CI.

**Pre-commit hook:** Check 3 (Python bare-except) exists. No Check 9 (JS silent catch). 23+ days since run 3 recommendation.

---

### Idea 1: JS Silent Catch Pre-commit Guard (Check 9) + AdminAnalyticsPage Fix
**Evidence:** Original violations FIXED manually → pattern recurred in AdminAnalyticsPage.jsx:117-122 (6 new instances). This is the strongest possible confirmation that one-off patches don't hold — the class recurs. Pre-commit guard = system fix. 21-issue sprint incoming = more JS surface area. Pre-commit hook already has 8 checks (Python-side); JS equivalent missing.
**Action:** (1) Fix AdminAnalyticsPage.jsx:117-122 (add console.warn like the marketing page pattern). (2) Add Check 9 to scripts/hooks/pre-commit — grep staged .js/.jsx for `.catch(() => null)` and `.catch(() => {})`, block commits without `// ok-silent-catch` inline override.
**Impact:** Closes the regression loop: original violations fixed + new violations fixed + pre-commit blocks future ones. Sprint proceeds with guard active.
**Category:** code_health

---

### Idea 2: Wire golden eval harness to weekly CI schedule
**Evidence:** `backend/tests/evals/` created today (`7854ede`). `test_lead_qualifier_golden.py` has proper structure (pytestmark skipif, 80% pass threshold, parametrized on json). NOT wired to any GH Actions workflow. Onboarding-v2 sprint (21 issues) may touch lead qualifier registry indirectly.
**Action:** Add `.github/workflows/lead-qualifier-eval.yml` with `schedule: cron: '0 8 * * 1'` (weekly Monday). Requires `ANTHROPIC_API_KEY` + `LEAD_QUALIFIER_AGENT_ID` GH Secrets. Steps: checkout → setup Python → install deps → `RUN_LEAD_QUALIFIER_EVAL=1 pytest backend/tests/evals/test_lead_qualifier_golden.py -v`.
**Impact:** Catch AI quality regressions before they ship. First eval harness in CI. Pattern for future evals (KB, booking agent, etc.).
**Category:** agent_performance

---

### Idea 3: Fix em-dash in WizardStepAutoKB.jsx → wire check_project_invariants.py
**Evidence:** Run 8 winner (`037865f`, 2026-04-25). `scripts/check_project_invariants.py` exists (stdlib-only, designed for CI). Blocked: WizardStepAutoKB.jsx:140/172/254 em-dash (—) violations. Onboarding-v2 sprint = more onboarding code = more naming-violation risk.
**Action:** (1) Grep WizardStepAutoKB.jsx for em-dashes at lines 140/172/254. Determine if they're in string literals (fix: replace with ASCII) or in JSX content (fix: add em-dash to invariants exclusion list). (2) Wire `python scripts/check_project_invariants.py` into scripts/hooks/pre-commit.
**Impact:** Run 8 winner finally implemented. client_id/status/areas_of_interest violations blocked at commit time. Moratorium: second-oldest after run 3.
**Category:** code_health

---

### Idea 4: Bug patterns monthly split (2,320 lines)
**Evidence:** `docs/dev-knowledge/bug-patterns.md` now 2,320 lines (was 2,204 in run 7, noted as parking-lot item since run 7). Auto-logger writes to it on every fix commit. Growing ~50 lines/week. Memory-tiered-retrieval rule says grep before full-read — single-file bug patterns breaks that pattern.
**Action:** Split into `docs/dev-knowledge/bug-patterns/2026-03.md`, `2026-04.md`, `INDEX.md` (listing months). Update auto-logger path in `.github/workflows/auto-log-bug.yml`.
**Impact:** Faster Claude reads. Prevents single unmanageable file.
**Category:** workflow

---

### Idea 5: Onboarding V2 characterization tests before sprint
**Evidence:** `plans/onboarding-v2_plan.md` created today (21 issues, 409 lines). Major sprint imminent. widget_helpers.py split (`6cf4646`) was done without pre-existing tests — resulted in `implemented_unverified` status still in governance. Same risk with 21 onboarding issues: sprint without safety net.
**Action:** Before any onboarding-v2 issue begins: write `backend/tests/test_onboarding_characterization.py` covering current behavior of `POST /api/onboarding/start`, `complete_step`, `get_wizard_state`. These pin current API contract so regressions are immediately visible.
**Impact:** Sprint with safety net. Prevents another `implemented_unverified` entry in governance.
**Category:** workflow
