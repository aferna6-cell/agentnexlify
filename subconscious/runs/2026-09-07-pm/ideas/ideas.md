# Ideas — Run 118 (2026-09-07-pm)

## Evidence Digest

- **Step 9L CONFIRMED implemented** (PR #804, commit `88dac49`, 2026-09-07). grep=2 in SKILL.md. Escalation condition resolved. First execution in tomorrow's nightly.
- **Skill discovery HIGH priority: `meter-ai-endpoint` skill** — 9 metering commits in 7 days (#792–#803). Each retrofit: 400–1726 test lines, 30–60 min. Pattern recurs every time a new AI route ships without a metering guard.
- **os_tool_executions.py** — 783L, last commit f22ef04 2026-09-03 (4 days stable). Governance mandate "10d+" condition NOT met yet. Deferred.
- **KB stale** — last compile 2026-08-26 (12 days). Step 9F/9G should have flagged this; verify next nightly.
- **Dependabot PRs merging** — 5 PRs merged since last run (#816, #813, #817, #812, #630). Step 9J improving.
- **`from __future__ import annotations` spreading in os_workflows/** — nightly filed GH issue.
- **pr-check.yml** — 9 manual pytest-list appends in one week; fragile 200-column line. Skill discovery rejected automation as "infrastructure change."

---

### Idea 1: Create `meter-ai-endpoint` Skill

**Evidence:** 9 metering commits (#792–#803) in 7 days — highest signal of any pattern this week per skill discovery 2026-09-07. Each retrofit required: `reserve_ai_tokens`, `record_ai_usage`, `release_ai_token_reservation` pattern, `_load_<service>_budget_tenant()` helper, 4 mandatory test cases (deny/success/failed-record/missing-tenant), CI line in pr-check.yml. Every step is mechanical but error-prone (wrong import alias, missing release branch, CI omission). Without the skill, each new AI route starts unguarded until Step 9L catches it and a 3-day retrofit sprint begins.

**Action:** Create `.claude/skills/meter-ai-endpoint/SKILL.md` — 6-step checklist: identify call site from `check_ai_metering.py` output, add imports, write `_load_<service>_budget_tenant()`, wrap call in reserve/record/release lifecycle, write 4 test cases, append to pr-check.yml pytest list.

**Impact:** 30–60 min saved per endpoint; eliminates metering debt accumulation; closes the gap between Step 9L detecting a violation and a developer knowing the exact fix pattern.

**Category:** workflow_efficiency

---

### Idea 2: Update `ai-feature-pattern` SKILL.md to Cross-Reference Metering

**Evidence:** `ai-feature-pattern` (v1.1.0) covers prompt engineering and API call template but has no mention of the reserve/record/release lifecycle. Skill discovery 2026-09-07 explicitly flagged this: "The skills should cross-reference each other." Every session that invokes `ai-feature-pattern` to build a new AI endpoint currently gets no metering guidance.

**Action:** Add a "Step 5. Metering (Required for production paths)" section to `.claude/skills/ai-feature-pattern/SKILL.md` pointing to the `meter-ai-endpoint` skill and `check_ai_metering.py`.

**Impact:** Prevents unmetered paths at authoring time, not just at detection time. Low effort (doc edit). Closes the upstream gap that Step 9L catches downstream.

**Category:** code_health

---

### Idea 3: os_tool_executions.py God Class Split

**Evidence:** File is 783L, last commit f22ef04 (2026-09-03, 4 days ago). Governance mandate: "10d+ stable: god class split is run 118 winner." Condition: NOT met (4d < 10d). Split still warranted at 783L under CLAUDE.md Rule 9 (>600 lines → factor first). Defers cleanly — file is not in active development.

**Action:** Split `backend/services/os_tool_executions.py` into `os_tool_executor_core.py` (execution lifecycle), `os_tool_registry.py` (catalog lookup), and `os_tool_result_parser.py` (output normalization). Extract any public API surface into `__init__.py`.

**Impact:** Reduces blast radius on a core OS automation file; makes each concern independently testable. Blocked until 10d+ stability confirmed (run 119 candidate).

**Category:** code_health

---

### Idea 4: Step 9J Token Budget Diagnosis and Fix

**Evidence:** 17/19 Dependabot PRs consistently skipped across 3 consecutive nightlies. nightly-commit-review consumes most of its token budget on earlier steps before reaching Step 9J. Governance mandate (run_116_mandate) item 6: "identify where the 17-skip token budget limit hits — which step consumes the budget before Step 9J processes all 19 PRs?"

**Action:** Add a token-budget checkpoint after Step 9I that logs budget remaining. If Step 9J sees >5 PRs eligible but only processes 2, move Step 9J earlier in the nightly execution order (before steps that have large file reads).

**Impact:** Enables full Dependabot auto-merge coverage. Currently 17/19 PRs skip = ~15+ CVE days of unnecessary exposure per cycle.

**Category:** operational

---

### Idea 5: `staging-preflight` Skill

**Evidence:** 2 preflight scripts in one week (`scripts/billing_staging_smoke.py`, `scripts/website_connect_migration201_preflight.py`) with diverging naming and structure. Skill discovery 2026-09-07 rated MEDIUM priority. Pattern: `--dry-run`/`--env` flags, `RunResult` dataclass, named-check functions, `main()` summary.

**Action:** Create `.claude/skills/staging-preflight/SKILL.md` — 3-step checklist: create `scripts/<feature>_staging_<preflight|smoke>.py` with standard shape, create `tests/test_<feature>_staging_readiness.py` (dry-run contract tests), do NOT add to CI (live credentials required).

**Impact:** 20–30 min saved per preflight; standardizes pattern; prevents naming drift.

**Category:** workflow_efficiency
