# Ideas — Run 13 (2026-05-02)

Evidence window: 2 days (2026-05-01 → 2026-05-02).

**Moratorium status:** ACTIVE (4 pending approvals; lift = ≤3).
**Oldest pending winner:** JS Silent Catch Guard — run 3 (2026-04-11, day 21).
**Constraints:** No new winners may be added to active_directions until pending ≤ 3.

---

### Idea 1: JS Silent Catch Check 10 + AdminAnalyticsPage.jsx Fix
**Evidence:** AdminAnalyticsPage.jsx:117-122 confirmed: 6 `.catch(() => null)` (grep, this run). Pre-commit has exactly 9 checks (`echo -n` count = 9) — Check 10 slot open. Onboarding V2 sprint (21 issues) started — every new JSX file is a vector. Run 12 winner is this exact item (unimplemented). Moratorium mandate: oldest pending at 21 days.
**Action:** (1) Fix AdminAnalyticsPage.jsx:117-122 — add `console.warn` to 6 silent catches. (2) Add Check 10 block to `scripts/hooks/pre-commit`. (3) Test guard. S-effort, zero deps.
**Impact:** Breaks pattern of silent API failures in dashboard. Prevents recurrence across Onboarding V2 sprint files. Closes Issue #109. Moratorium drops 4 → 3 → lifts.
**Category:** code_health

---

### Idea 2: email_sequences N+1 Query Fix
**Evidence:** Nightly review 2026-05-02 opened Issue #112. `list_enrollments` (lines 708–724): 1 DB call per enrollment row = 1001 queries for 1000 enrollments. `list_sequences` (lines 256–283): 101 queries per 50-sequence load. `email_sequences.py` shipped via `fa466ca` on 2026-05-01 — already indexed and in production. At scale (tenants with 500+ enrollments), this hits Supabase per-request rate limit.
**Action:** Refactor `list_enrollments` to bulk-fetch lead info via `.in_()`. Refactor `list_sequences` to aggregate step_count and enrollment_count in Python post-fetch. Backend-dev task, ~60 LOC change.
**Impact:** Prevents Supabase rate-limit 429s for any tenant with >500 enrolled leads. Fixes latency before it becomes a support ticket.
**Category:** code_health / operational

---

### Idea 3: Scope em-dash Check + Wire check_project_invariants.py
**Evidence:** Run 8 winner (2026-04-25) recommended wiring `check_project_invariants.py` into pre-commit. Direct execution still shows 9 violations (WizardStepAutoKB.jsx:2/140/172/254 + AutomationActivityCard.jsx:156/172/188/251/389). The em-dash rule fires on JSX render chars (`|| '—'`). Fix: add `.jsx/.tsx` exclusion (one line in `check_project_invariants.py`). Then wire as Check 11. Two-step: fix em-dash scope → add pre-commit check.
**Action:** (1) Add `if path.endswith(('.jsx', '.tsx')): continue` to the em-dash check in `check_project_invariants.py`. (2) Wire script as Check 11 in `scripts/hooks/pre-commit`. M-effort (two steps + verify).
**Impact:** Enforces client_id / status / areas_of_interest naming invariants on every commit. Blocks the class of schema drift bugs that have caused 3+ production incidents.
**Category:** code_health

---

### Idea 4: Wire Golden Eval Harness to CI
**Evidence:** `backend/tests/evals/test_lead_qualifier_golden.py` + `lead_qualifier_golden.json` added in `7854ede` (2026-04-30). Env-var gated, 80% pass threshold. Issue #110 (nightly 2026-05-01) formally tracks CI wiring. Parking lot ROI 2.5 — highest in lot. Earmarked as "first post-moratorium winner" since run 11.
**Action:** Add `.github/workflows/lead-qualifier-eval.yml` with weekly Monday cron. Set `LEAD_QUALIFIER_AGENT_ID` in GH Secrets. S-effort for CI file, M-effort for secrets coordination.
**Impact:** Catches regression in lead qualifier quality before it reaches tenants. First automated quality gate on AI agent output.
**Category:** agent_performance / operational

---

### Idea 5: Reasoning-Trace Comment Scanner (Pre-commit Check 12)
**Evidence:** Daily log 2026-05-01 P2 task: "Implement reasoning-trace comment scanner pre-commit hook (LOW finding from `8050912`)." `_mask_phone` had `// Step 1:`, `// thinking:` inline reasoning markers committed to production. These are code smell from AI-generated code that didn't clean up its trace output. Pattern recurs across AI-assisted files.
**Action:** Add bash grep in `scripts/hooks/pre-commit` scanning staged `.py/.js/.jsx` files for patterns `# Step [0-9]:\|# Thinking:\|// Step [0-9]:\|// Thinking:`. WARN on match (not FAIL — too disruptive as hard block). S-effort.
**Impact:** Flags when AI reasoning scaffolding leaks into committed code. Low false-positive rate (patterns are rarely intentional).
**Category:** code_health / workflow
