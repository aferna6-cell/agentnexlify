# Candidate Ideas — Run 118 (2026-09-08)

## Evidence Digest

- Step 9L IMPLEMENTED (PR #804, 88dac49, 2026-09-07). `check_ai_metering.py` confirmed working: live scan finds 30+ violations across 16 router files and 14 service files.
- Skill discovery 2026-09-07 explicitly proposed `meter-ai-endpoint` as highest-signal skill of the week: 9 metering commits, 30-60 min per endpoint, mechanical but error-prone.
- os_tool_executions.py: 783L, last commit 2026-09-03 (5+ days stable). Rule 9 threshold crossed.
- Step 9J: 17/19 Dependabot PRs skipped per run due to token budget. Root cause uninvestigated.
- Nightly-2026-09-08: 2 `from __future__ import annotations` fixed in service files; 5 test files flagged MEDIUM → GH issue filed. Pattern spreading in os_workflows/.
- Issue-to-pr-loop still stalled (GH #399 AUTOPILOT_GH_TOKEN expired) — Step 9L violations won't auto-fix.

---

### Idea 1: Create `meter-ai-endpoint` skill

**Evidence:** 9 metering commits this week (commits bc0332b, 1d056f3, 3e1a023, 9de7f60, 3b93367, 0b41f4d, 9b1381b, 47f14d3, c2e5864). Skill discovery 2026-09-07 proposed exact pattern. 30+ violations live. Issue-to-pr-loop stalled so violations won't auto-fix — manual skill invocation is the path. `check_ai_metering.py` already exists as the scanner.
**Action:** Create `.claude/skills/meter-ai-endpoint/SKILL.md` with 6-step checklist (identify violation, add imports, write `_load_budget_tenant`, wrap call in reserve/record/release, write 4 test cases, add to CI pytest command).
**Impact:** 30-60 min per endpoint → ~10 min per endpoint. 30+ violations × 20 min saved = 10+ engineer-hours. Prevents next emergency metering sprint.
**Category:** workflow_efficiency

---

### Idea 2: Split `os_tool_executions.py` god class (783L)

**Evidence:** 783L confirmed, 5+ days stable. CLAUDE.md Rule 9: >600L = factor before adding. Parking lot since run 115. Step 9L now confirmed — governance condition for promotion met.
**Action:** Write implementation sketch: identify the module boundaries (tool registry, execution engine, result handling, error recovery), propose 3-4 extract targets with file names and line ranges. Recommend compound-engineering session to execute.
**Impact:** Code maintainability. Prevents blast radius compounding as Agent OS features grow.
**Category:** code_health

---

### Idea 3: Fix Step 9J token budget (17/19 Dependabot PRs skipped)

**Evidence:** 17/19 Dependabot PRs skipped every nightly per runs 115/116/117. Step 9J is 10% effective. Run_117_mandate explicitly asked for root cause investigation. CVE patch latency risk.
**Action:** Read one recent nightly transcript to identify which preceding step consumes the token budget before Step 9J processes all 19 PRs. Propose a targeted fix (step ordering or cap adjustment).
**Impact:** Step 9J goes from 10% → 100% effective. Security patches within 24h of CI passing vs indefinite delay.
**Category:** operational

---

### Idea 4: Add pre-commit check for `from __future__ import annotations` in test files

**Evidence:** Nightly-2026-09-08 found 5 test files with the import (test_website_connect.py, test_local_seo_handlers.py, test_os_invoice_actions.py, test_os_calendar_crm.py, test_os_invoice_e2e.py). Current pre-commit hook only checks service/router files. Pattern spreading in os_workflows/ (shadow_planner.py, planner_bakeoff.py, tool_catalog.py — 3 fixed in last 3 days). Will recur without a gate.
**Action:** Extend pre-commit hook pattern in `scripts/install-hooks.sh` or the pre-commit hook file to include `backend/tests/` in the `from __future__ import annotations` check.
**Impact:** Stops the pattern from spreading to test files. Prevents false sense of safety (if a test file gains a Pydantic import later, the annotation silently breaks it).
**Category:** code_health

---

### Idea 5: Create `staging-preflight` skill (skill discovery proposal)

**Evidence:** Skill discovery 2026-09-07 proposed `staging-preflight` as second-highest pattern. PR #779 (test_billing_dry_run_staging.py) and other staging scripts follow a consistent but unwired pattern. 3-4 features per month need staged check-only passes before prod.
**Action:** Create `.claude/skills/staging-preflight/SKILL.md` with template for `--dry-run` / `--env` scripts with `RunResult` dataclass and table summary output.
**Impact:** Reduces deploy risk on staged features. Consistent check-only UX across all features.
**Category:** workflow_efficiency
